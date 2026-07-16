"""
Agent 图编排模块 — 使用 LangGraph 将 LLM 与工具节点连接。

职责：
- 构建 StateGraph 定义 Agent 工作流（agent_node → 工具调用 → agent_node → END）
- 编译可执行图（带内存检查点，支持多轮对话）
- 提供 run_agent 入口函数，将 YOLOv11 检测结果注入 Agent 上下文

流程：
    用户消息 + YOLOv11 检测结果
        → agent_node (LLM 推理，决定是否调用工具)
        → router_node (条件路由: 工具调用 → tool_node, 否则 → END)
        → tool_node (执行工具后返回 agent_node)
        → agent_node (基于工具结果生成最终回复)
        → END
"""

import json
import logging
from typing import Annotated, Any, Optional, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.config.settings import settings
from app.services.agent_prompts import (
    SYSTEM_PROMPT,
    format_detection_for_prompt,
)
from app.services.agent_tools import (
    calculate_total_nutrition,
    detect_food,
    query_food_by_category,
    query_food_calories,
    save_detection_record,
)

logger = logging.getLogger(__name__)

# ==================================================================
# Agent 状态定义
# ==================================================================


class AgentState(TypedDict, total=False):
    """LangGraph Agent 的状态结构。

    messages: 对话历史（自动追加，使用 LangGraph 的 add_messages reducer）
    detections: YOLOv11 检测结果列表（可选，有检测结果时传入）
    user_id: 当前用户 ID（可选，用于个性化查询）
    analysis_result: 最终分析结果（Agent 完成后填充）
    """
    messages: Annotated[list[BaseMessage], add_messages]
    detections: Optional[list[dict]]
    user_id: Optional[int]
    analysis_result: Optional[str]
    image_id: Optional[str]


# ==================================================================
# 工具列表（注册给 LLM 调用）
# ==================================================================

# 注意：LangChain @tool 装饰器创建的是同步工具，但我们的实现是 async 的。
# 这里使用 Tool 的 StructuredTool 包装来确保兼容性。
from langchain_core.tools import StructuredTool

AGENT_TOOLS = [
    StructuredTool.from_function(
        coroutine=detect_food,
        name="detect_food",
        description="识别已上传餐食图片中的食物。必须传入系统提供的 image_id，可选置信度阈值。返回标准 YOLO detections JSON。",
    ),
    StructuredTool.from_function(
        coroutine=query_food_calories,
        name="query_food_calories",
        description="查询指定食物的营养数据（每100g）。输入为食物名称（中文或英文）。返回热量、蛋白质、脂肪、碳水化合物和膳食纤维。",
    ),
    StructuredTool.from_function(
        coroutine=query_food_by_category,
        name="query_food_by_category",
        description="查询指定分类下的所有食物及其营养数据。输入为食物分类名称（如 fruit, meat, vegetable, staple）。",
    ),
    StructuredTool.from_function(
        coroutine=calculate_total_nutrition,
        name="calculate_total_nutrition",
        description="根据食物清单和估算重量计算总营养摄入。输入为 JSON 字符串: [{'food_name': 'apple', 'estimated_weight_g': 200}]。",
    ),
    StructuredTool.from_function(
        coroutine=save_detection_record,
        name="save_detection_record",
        description="将 YOLOv11 检测结果持久化保存到数据库。输入为 user_id(int), scene_id(int), detections_json(str)。",
    ),
]

# ==================================================================
# LLM 实例
# ==================================================================

_llm: Optional[ChatOpenAI] = None


def _get_llm() -> ChatOpenAI:
    """获取 LLM 实例（延迟初始化，绑定工具）。"""
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_BASE_URL,
            temperature=0.3,
            streaming=True,
        )
    return _llm.bind_tools(AGENT_TOOLS)


# ==================================================================
# 图节点定义
# ==================================================================


async def agent_node(state: AgentState) -> dict:
    """Agent 节点：调用 LLM 进行推理。

    将当前对话历史（messages）发给 LLM，LLM 可以选择：
    - 直接回复用户
    - 调用一个或多个工具

    Args:
        state: 当前 Agent 状态

    Returns:
        包含 LLM 响应（AIMessage）的字典
    """
    llm_with_tools = _get_llm()
    messages = state["messages"]

    # 确保系统提示词在最前面
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)

    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}


async def router_node(state: AgentState) -> str:
    """路由节点：判断 LLM 是否需要调用工具。

    Args:
        state: 当前 Agent 状态

    Returns:
        "tools" — 需要调用工具，继续到 tool_node
        END — 不需要调用工具，结束流程
    """
    messages = state["messages"]
    last_message = messages[-1] if messages else None

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return END


# ==================================================================
# 图编译
# ==================================================================

# 内存检查点（保存对话历史，支持多轮对话）
_memory = MemorySaver()


def build_agent_graph() -> StateGraph:
    """构建 LangGraph Agent 工作流图。

    图结构：
        START → agent_node → router_node:
                   ├── "tools" → tool_node → agent_node（循环）
                   └── END

    Returns:
        未编译的 StateGraph
    """
    workflow = StateGraph(AgentState)

    # 工具节点 — 使用 LangGraph 内置 ToolNode 自动执行工具调用
    tool_node = ToolNode(AGENT_TOOLS)

    # 注册节点
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)

    # 边
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        router_node,
        {
            "tools": "tools",
            END: END,
        },
    )
    workflow.add_edge("tools", "agent")  # 工具执行后返回 agent 继续推理

    return workflow


def get_agent_executor():
    """获取编译好的 Agent 执行器（带内存检查点）。

    Returns:
        已编译的 CompiledGraph，可直接调用 ainvoke
    """
    graph = build_agent_graph()
    return graph.compile(checkpointer=_memory)


# 模块级单例
_agent_executor = None


def _get_executor():
    global _agent_executor
    if _agent_executor is None:
        _agent_executor = get_agent_executor()
    return _agent_executor


# ==================================================================
# 公开入口
# ==================================================================


async def run_agent(
    session_id: str,
    user_message: str,
    detections: Optional[list[dict]] = None,
    image_id: Optional[str] = None,
    user_id: Optional[int] = None,
) -> dict:
    """运行 Agent 管道的主入口函数。

    将用户的自然语言消息和 YOLOv11 检测结果一起传给 Agent，
    由 LLM 驱动工具调用完成营养分析，最后返回结构化结果。

    典型用法：
        result = await run_agent(
            session_id="session-001",
            user_message="我刚刚吃了这些食物，请帮我分析一下",
            detections=[{"class_name": "apple", "class_name_cn": "苹果", "confidence": 0.95, "bbox": [10,20,200,300]}],
            user_id=1,
        )

    Args:
        session_id: 会话标识（用于 LangGraph 内存检查点，支持多轮对话）
        user_message: 用户的自然语言输入
        detections: YOLOv11 检测结果列表（可选）
        user_id: 用户 ID（可选）

    Returns:
        {
            "response": "Agent 的最终文本回复",
            "tool_calls": ["..."],        # 工具调用日志（可选）
            "analysis_result": "...",     # 结构化分析结果（可选）
        }
    """
    executor = _get_executor()

    # 构造初始消息
    messages = []

    # 图片只以安全 image_id 进入状态；由 Agent 自主决定并调用 detect_food。
    if image_id:
        messages.append(
            HumanMessage(
                content=(
                    "[IMAGE_CONTEXT]\n"
                    f"用户已上传一张餐食图片，image_id={image_id}。\n"
                    "你必须先调用 detect_food 工具观察图片检测结果，不能猜测图片内容；"
                    "得到食物列表后，再按用户问题决定是否查询和计算营养。"
                )
            )
        )

    # 兼容已有系统直接提供检测结果的场景
    if detections:
        detection_text = format_detection_for_prompt(detections)
        context_msg = (
            "YOLOv11 视觉模型检测到以下食物：\n\n"
            f"{detection_text}\n\n"
            "请查询这些食物的营养数据，计算总营养，并给出饮食建议。"
        )
        messages.append(HumanMessage(content=context_msg))

    # 用户消息
    if user_message:
        messages.append(HumanMessage(content=user_message))

    if not messages:
        return {"response": "未提供任何消息或检测结果。", "tool_calls": [], "analysis_result": None}

    # 配置（session_id 作为 thread_id 用于内存检查点）
    config = {
        "configurable": {"thread_id": session_id},
        # 防止模型持续重复调用工具而形成无限循环。
        "recursion_limit": 12,
    }

    # 构建初始状态
    initial_state: AgentState = {
        "messages": messages,
        "detections": detections,
        "image_id": image_id,
        "user_id": user_id,
        "analysis_result": None,
    }

    try:
        # 执行图
        final_state = await executor.ainvoke(initial_state, config)

        # 提取最后一条 AI 消息作为回复
        all_messages = final_state.get("messages", [])
        response_text = ""
        tool_calls_log = []
        detected_foods = []
        detection_mode = None

        for msg in all_messages:
            if isinstance(msg, AIMessage):
                if msg.content:
                    response_text = msg.content
                if msg.tool_calls:
                    for tc in msg.tool_calls:
                        tool_calls_log.append({
                            "name": tc.get("name", "unknown"),
                            "args": tc.get("args", {}),
                        })
            elif isinstance(msg, ToolMessage) and getattr(msg, "name", None) == "detect_food":
                try:
                    tool_result = json.loads(msg.content)
                    if tool_result.get("success"):
                        detected_foods = tool_result.get("detections", [])
                        detection_mode = tool_result.get("mode")
                except (json.JSONDecodeError, TypeError):
                    logger.warning("无法解析 detect_food 工具结果")

        analysis = final_state.get("analysis_result")

        return {
            "response": response_text,
            "tool_calls": tool_calls_log,
            "analysis_result": analysis,
            "detections": detected_foods,
            "detection_mode": detection_mode,
        }

    except Exception as exc:
        logger.exception("Agent 执行失败")
        return {
            "response": "抱歉，营养分析暂时不可用，请稍后重试。",
            "tool_calls": [],
            "analysis_result": None,
            "detections": [],
            "detection_mode": None,
        }
