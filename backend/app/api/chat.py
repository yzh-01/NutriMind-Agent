"""NutriMind 营养智能体对话 API。"""

import uuid
import json
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.core.security import get_current_user
from app.config.settings import settings
from app.entity.db_models import BodyProfile, GoalProfile, User
from app.database.session import get_db, get_session_local
from app.entity.schemas import (
    BoundingBox, ChatRequest, ChatResponse, ChatSessionCreate,
    ChatSessionResponse, ImageChatResponse,
)
from app.services.agent_graph import run_agent, stream_agent
from app.services import chat_service
from app.services.image_store import image_store
from app.services.knowledge_service import knowledge_service

import asyncio
from fastapi.responses import StreamingResponse
from typing import AsyncIterator

# 持有后台抽取任务引用，避免被 GC 提前回收
_graph_tasks: set[asyncio.Task] = set()


async def _extract_conversation_graph(user_message: str, response_text: str) -> int:
    """从一轮完整对话抽取食物实体，并等待数据库提交完成。"""
    combined = f"{user_message}\n\n{response_text}".strip()
    if not combined:
        return 0
    try:
        count = await knowledge_service.extract_and_store_graph(combined, source="对话抽取")
        logger.info("对话图谱抽取完成：新增/更新 %d 种食物", count)
        return count
    except Exception as exc:
        logger.warning("对话图谱抽取失败: %s", exc)
        return 0


def _schedule_graph_extraction(user_message: str, response_text: str) -> None:
    """为非流式接口调度图谱抽取，并持有任务引用直到完成。"""
    if not f"{user_message}{response_text}".strip():
        return

    async def _run():
        await _extract_conversation_graph(user_message, response_text)

    task = asyncio.create_task(_run())
    _graph_tasks.add(task)
    task.add_done_callback(_graph_tasks.discard)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["AI 对话"])


def _agent_profile(db: Session | None, user_id: int | None) -> dict | None:
    """读取营养相关资料，并排除手机号、邮箱、用户名等账户信息。"""
    if db is None or user_id is None:
        return None
    try:
        body = db.query(BodyProfile).filter(BodyProfile.user_id == user_id).first()
        goal = db.query(GoalProfile).filter(GoalProfile.user_id == user_id).first()
        return {
            "body_profile": {
                "current_weight_kg": body.current_weight_kg,
                "height_cm": body.height_cm,
                "birth_date": body.birth_date,
                "sex_for_calculation": body.sex_for_calculation,
                "activity_level": body.activity_level,
            } if body else None,
            "goal": {
                "mode": goal.mode,
                "target_weight_kg": goal.target_weight_kg,
                "daily_calories_kcal": goal.daily_calories_kcal,
                "protein_target_g": goal.protein_target_g,
                "training_days_per_week": goal.training_days_per_week,
            } if goal else None,
        }
    except Exception as exc:
        logger.warning("读取 Agent 个性化资料失败，将使用通用上下文: %s", exc)
        return None


def _validate_request(request: ChatRequest) -> str:
    message = request.message.strip()
    if not message and not request.detections:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="消息和检测结果不能同时为空",
        )
    return message


async def _invoke_chat(
    request: ChatRequest, thread_prefix: str, user_id: int | None, db: Session | None = None,
) -> ChatResponse:
    message = _validate_request(request)
    session_id = request.session_id or str(uuid.uuid4())
    persisted_session = None
    history = None
    if db is not None and user_id is not None:
        try:
            persisted_session = chat_service.get_or_create_session(db, user_id, session_id, message)
            history = chat_service.history_as_langchain(persisted_session)
            chat_service.append_message(db, persisted_session, "user", message)
        except Exception as exc:
            db.rollback()
            persisted_session = None
            history = None
            logger.warning("会话持久化暂不可用，降级为进程内对话: %s", exc)

    result = await run_agent(
        session_id=f"{thread_prefix}:{session_id}",
        user_message=message,
        detections=[item.model_dump() for item in request.detections] or None,
        user_id=user_id,
        history=history,
        user_profile=_agent_profile(db, user_id),
    )
    if persisted_session is not None:
        try:
            chat_service.append_message(
                db, persisted_session, "assistant", result["response"], result.get("tool_calls", []),
            )
        except Exception as exc:
            db.rollback()
            logger.warning("保存智能体回复失败: %s", exc)

    # 对话结束后后台抽取食物实体进图谱
    _schedule_graph_extraction(message, result.get("response", ""))

    return ChatResponse(
        session_id=session_id,
        response=result["response"],
        tool_calls=result.get("tool_calls", []),
        analysis_result=result.get("analysis_result"),
    )


def _sse(event: dict) -> str:
    """把事件序列化为一条 SSE 记录。"""
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",  # 关闭 Nginx 缓冲，确保逐条下发
}


async def _stream_chat_events(
    *,
    session_id: str,
    message: str,
    thread_prefix: str,
    user_id: int | None,
    detections: list[dict] | None = None,
    image_id: str | None = None,
    extra_done: dict | None = None,
) -> AsyncIterator[str]:
    """驱动 stream_agent，并在完成事件发给前端前可靠持久化。"""
    db = get_session_local()() if user_id is not None else None
    persisted_session = None
    history = None
    assistant_saved = False
    streamed_text = ""
    if db is not None and user_id is not None:
        try:
            persisted_session = chat_service.get_or_create_session(db, user_id, session_id, message)
            history = chat_service.history_as_langchain(persisted_session)
            chat_service.append_message(
                db, persisted_session, "user", message, image_id=image_id,
            )
        except Exception as exc:
            db.rollback()
            persisted_session = None
            history = None
            logger.warning("会话持久化暂不可用，降级为进程内对话: %s", exc)

    # 先把 session_id 告知前端，便于新会话立即绑定
    yield _sse({"type": "session", "session_id": session_id})

    try:
        async for event in stream_agent(
            session_id=f"{thread_prefix}:{session_id}",
            user_message=message,
            detections=detections,
            image_id=image_id,
            user_id=user_id,
            history=history,
            user_profile=_agent_profile(db, user_id),
        ):
            event_type = event.get("type")
            if event_type == "token":
                streamed_text += str(event.get("text") or "")
            elif event_type == "reset":
                streamed_text = ""
            elif event_type == "done":
                if extra_done:
                    event = {**event, **extra_done}
                response_text = str(event.get("response") or streamed_text)

                # 先通知前端进入同步阶段，避免图谱抽取期间被空闲超时误杀。
                yield _sse({"type": "sync", "stage": "persisting"})

                if persisted_session is not None:
                    try:
                        chat_service.append_message(
                            db,
                            persisted_session,
                            "assistant",
                            response_text,
                            event.get("tool_calls", []),
                        )
                        assistant_saved = True
                    except Exception as exc:
                        db.rollback()
                        logger.warning("保存流式智能体回复失败: %s", exc)

                graph_task = asyncio.create_task(
                    _extract_conversation_graph(message, response_text)
                )
                _graph_tasks.add(graph_task)
                graph_task.add_done_callback(_graph_tasks.discard)
                while not graph_task.done():
                    done, _ = await asyncio.wait({graph_task}, timeout=15)
                    if not done:
                        yield _sse({"type": "sync", "stage": "updating_graph"})
                graph_foods_count = graph_task.result()
                event = {**event, "graph_foods_count": graph_foods_count}
            elif event_type == "error":
                error_text = str(event.get("message") or "智能体处理失败，请稍后重试。")
                if persisted_session is not None:
                    try:
                        chat_service.append_message(
                            db, persisted_session, "assistant", f"回复生成失败：{error_text}",
                        )
                        assistant_saved = True
                    except Exception as exc:
                        db.rollback()
                        logger.warning("保存流式错误记录失败: %s", exc)
            yield _sse(event)
    except Exception:
        logger.exception("流式对话失败")
        error_text = "抱歉，营养分析暂时不可用，请稍后重试。"
        if persisted_session is not None and not assistant_saved:
            try:
                chat_service.append_message(
                    db, persisted_session, "assistant", f"回复生成失败：{error_text}",
                )
                assistant_saved = True
            except Exception as exc:
                db.rollback()
                logger.warning("保存流式异常记录失败: %s", exc)
        yield _sse({"type": "error", "message": error_text})
    finally:
        # 浏览器取消或网络断开时也给用户消息补上一条可恢复的助手记录。
        if persisted_session is not None and not assistant_saved:
            interrupted_text = streamed_text.strip()
            if interrupted_text:
                interrupted_text += "\n\n[流式连接中断，以上为已生成内容]"
            else:
                interrupted_text = "本次回复因流式连接中断，未能完整生成。"
            try:
                chat_service.append_message(db, persisted_session, "assistant", interrupted_text)
            except Exception as exc:
                db.rollback()
                logger.warning("保存流式中断记录失败: %s", exc)
        if db is not None:
            db.close()


@router.post("/message/stream")
async def send_message_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """流式发送消息（SSE）：智能体一边生成、前端一边显示，避免长请求超时。"""
    message = _validate_request(request)
    session_id = request.session_id or str(uuid.uuid4())
    generator = _stream_chat_events(
        session_id=session_id,
        message=message,
        thread_prefix=f"user:{current_user.id}",
        user_id=current_user.id,
        detections=[item.model_dump() for item in request.detections] or None,
    )
    return StreamingResponse(generator, media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    """发送消息，可同时携带 YOLO 食物检测结果并延续多轮会话。"""
    return await _invoke_chat(request, f"user:{current_user.id}", current_user.id, db)


@router.post("/mock-yolo", response_model=ChatResponse)
async def mock_yolo_chat(request: ChatRequest) -> ChatResponse:
    """用模拟 YOLO detections 联调完整智能体链路（仅 DEBUG 模式开放）。"""
    if not settings.DEBUG:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    return await _invoke_chat(request, "mock-yolo", None)


def _session_response(session, include_messages: bool = False) -> ChatSessionResponse:
    messages = []
    if include_messages:
        messages = [{
            "id": item.id, "role": item.role, "content": item.content,
            "image_id": item.image_id,
            "image_url": f"/api/chat/images/{item.image_id}" if item.image_id else None,
            "tool_calls": item.tool_calls or [], "created_at": item.created_at,
        } for item in session.messages]
    return ChatSessionResponse(
        session_id=session.session_uuid, title=session.title,
        created_at=session.created_at, updated_at=session.updated_at,
        messages=messages,
    )


@router.post("/sessions", response_model=ChatSessionResponse)
async def new_session(
    payload: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatSessionResponse:
    """显式创建一个空白新对话。"""
    session = chat_service.create_session(db, current_user.id, str(uuid.uuid4()), payload.title)
    return _session_response(session)


@router.get("/sessions", response_model=list[ChatSessionResponse])
async def get_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ChatSessionResponse]:
    """获取当前用户的历史对话列表。"""
    return [_session_response(item) for item in chat_service.list_sessions(db, current_user.id)]


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session_detail(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatSessionResponse:
    """加载完整历史，用同一 session_id 发消息即可从断点继续。"""
    session = chat_service.get_session(db, current_user.id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return _session_response(session, include_messages=True)


@router.delete("/sessions/{session_id}", status_code=204)
async def remove_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = chat_service.get_session(db, current_user.id, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    chat_service.delete_session(db, session)


async def _invoke_image_chat(
    *,
    file: UploadFile,
    message: str,
    session_id: str | None,
    thread_prefix: str,
    user_id: int | None,
    db: Session | None = None,
    mock_detections: list[dict] | None = None,
) -> ImageChatResponse:
    if not message.strip():
        raise HTTPException(status_code=422, detail="message 不能为空")
    content = await file.read(settings.MAX_IMAGE_SIZE_MB * 1024 * 1024 + 1)
    try:
        image_id = await image_store.save(
            content=content,
            content_type=file.content_type or "",
            mock_detections=mock_detections,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    external_session_id = session_id or str(uuid.uuid4())
    persisted_session = None
    history = None
    if db is not None and user_id is not None:
        try:
            persisted_session = chat_service.get_or_create_session(
                db, user_id, external_session_id, message,
            )
            history = chat_service.history_as_langchain(persisted_session)
            chat_service.append_message(
                db, persisted_session, "user", message.strip(), image_id=image_id,
            )
        except Exception as exc:
            db.rollback()
            persisted_session = None
            history = None
            logger.warning("图片会话持久化暂不可用，降级为进程内对话: %s", exc)
    result = await run_agent(
        session_id=f"{thread_prefix}:{external_session_id}",
        user_message=message.strip(),
        image_id=image_id,
        user_id=user_id,
        history=history,
        user_profile=_agent_profile(db, user_id),
    )
    if persisted_session is not None:
        try:
            chat_service.append_message(
                db, persisted_session, "assistant", result["response"],
                result.get("tool_calls", []),
            )
        except Exception as exc:
            db.rollback()
            logger.warning("保存图片会话智能体回复失败: %s", exc)
    return ImageChatResponse(
        session_id=external_session_id,
        image_id=image_id,
        detection_mode=result.get("detection_mode") or settings.DETECTION_MODE,
        detections=result.get("detections", []),
        response=result["response"],
        tool_calls=result.get("tool_calls", []),
        analysis_result=result.get("analysis_result"),
    )


@router.get("/images/{image_id}")
async def get_chat_image(
    image_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """读取当前用户历史消息中的图片，避免仅凭 image_id 越权访问。"""
    owned = chat_service.user_owns_image(db, current_user.id, image_id)
    if not owned:
        raise HTTPException(status_code=404, detail="图片不存在或无权访问")
    try:
        path = image_store.get_path(image_id)
    except (ValueError, FileNotFoundError):
        raise HTTPException(status_code=404, detail="图片不存在或已过期")
    media_types = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    return FileResponse(path, media_type=media_types.get(path.suffix.lower(), "application/octet-stream"))


@router.post("/image", response_model=ImageChatResponse)
async def analyze_image(
    file: UploadFile = File(..., description="餐食图片（JPG/PNG/WEBP，最大 10MB）"),
    message: str = Form(..., max_length=4000),
    session_id: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ImageChatResponse:
    """正式图片对话入口：Agent 主动调用真实 YOLO 工具（需要模型文件）。"""
    return await _invoke_image_chat(
        file=file,
        message=message,
        session_id=session_id,
        thread_prefix=f"user:{current_user.id}:image",
        user_id=current_user.id,
        db=db,
    )


@router.post("/image/stream")
async def analyze_image_stream(
    file: UploadFile = File(..., description="餐食图片（JPG/PNG/WEBP，最大 10MB）"),
    message: str = Form(..., max_length=4000),
    session_id: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """流式图片对话（SSE）：Agent 调用真实 YOLO 工具，逐步回传分析结果。"""
    if not message.strip():
        raise HTTPException(status_code=422, detail="message 不能为空")
    content = await file.read(settings.MAX_IMAGE_SIZE_MB * 1024 * 1024 + 1)
    try:
        image_id = await image_store.save(content=content, content_type=file.content_type or "")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    external_session_id = session_id or str(uuid.uuid4())
    generator = _stream_chat_events(
        session_id=external_session_id,
        message=message.strip(),
        thread_prefix=f"user:{current_user.id}:image",
        user_id=current_user.id,
        image_id=image_id,
        extra_done={"image_id": image_id},
    )
    return StreamingResponse(generator, media_type="text/event-stream", headers=SSE_HEADERS)


@router.post("/image/mock", response_model=ImageChatResponse)
async def analyze_image_with_mock_yolo(
    file: UploadFile = File(..., description="任意测试餐食图片（工具调用仍会发生）"),
    message: str = Form(..., max_length=4000),
    mock_detections: str = Form(..., description="YOLO detections JSON 数组"),
    session_id: str | None = Form(default=None),
) -> ImageChatResponse:
    """开发联调入口：上传图片，Agent 调用 detect_food 获取随请求提供的模拟结果。"""
    if not settings.DEBUG:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")
    try:
        raw_detections = json.loads(mock_detections)
        if not isinstance(raw_detections, list):
            raise ValueError("mock_detections 必须是 JSON 数组")
        detections = [BoundingBox.model_validate(item).model_dump() for item in raw_detections]
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"无效的 mock_detections: {exc}") from exc

    return await _invoke_image_chat(
        file=file,
        message=message,
        session_id=session_id,
        thread_prefix="mock-image",
        user_id=None,
        mock_detections=detections,
    )
