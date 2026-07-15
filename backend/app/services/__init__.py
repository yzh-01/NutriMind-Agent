"""NutriMind-Agent 业务服务层（AI/算法工程师工作目录）。

本层包含所有核心业务逻辑：
- detection_service: YOLO26 模型加载与图片推理
- training_service: 模型训练任务管理与后台训练执行
- data_utils: 数据集准备与预处理工具
- agent_graph: LangGraph Agent 编排
- agent_tools: Agent 可调用工具（卡路里查询等）
- agent_prompts: Agent 系统提示词
"""

from app.services.detection_service import detection_service  # noqa: F401
from app.services.training_service import training_service  # noqa: F401
from app.services.user_service import user_service  # noqa: F401
from app.services.knowledge_service import knowledge_service  # noqa: F401
