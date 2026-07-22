"""智能体会话持久化服务。"""

from datetime import datetime
from typing import Iterable

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from sqlalchemy.orm import Session

from app.entity.db_models import ChatMessage, ChatSession


def create_session(db: Session, user_id: int, session_id: str, title: str | None = None) -> ChatSession:
    session = ChatSession(
        session_uuid=session_id,
        user_id=user_id,
        title=(title or "新对话").strip() or "新对话",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, user_id: int, session_id: str) -> ChatSession | None:
    return (
        db.query(ChatSession)
        .filter(ChatSession.session_uuid == session_id, ChatSession.user_id == user_id)
        .first()
    )


def get_or_create_session(db: Session, user_id: int, session_id: str, first_message: str = "") -> ChatSession:
    session = get_session(db, user_id, session_id)
    if session:
        return session
    title = first_message.strip().replace("\n", " ")[:50] or "新对话"
    return create_session(db, user_id, session_id, title)


def list_sessions(db: Session, user_id: int, limit: int = 50) -> list[ChatSession]:
    return (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user_id)
        .order_by(ChatSession.updated_at.desc())
        .limit(limit)
        .all()
    )


def append_message(
    db: Session,
    session: ChatSession,
    role: str,
    content: str,
    tool_calls: list[dict] | None = None,
    image_id: str | None = None,
) -> ChatMessage:
    message = ChatMessage(
        session_id=session.id,
        role=role,
        content=content,
        image_id=image_id,
        tool_calls=tool_calls or None,
    )
    session.updated_at = datetime.now()
    db.add(message)
    db.add(session)
    db.commit()
    db.refresh(message)
    return message


def history_as_langchain(session: ChatSession, exclude_last: int = 0) -> list[BaseMessage]:
    messages: Iterable[ChatMessage] = session.messages
    if exclude_last:
        messages = list(messages)[:-exclude_last]
    result: list[BaseMessage] = []
    for item in messages:
        if item.role == "user":
            result.append(HumanMessage(content=item.content))
        elif item.role == "assistant":
            result.append(AIMessage(content=item.content))
    return result


def delete_session(db: Session, session: ChatSession) -> None:
    db.delete(session)
    db.commit()


def user_owns_image(db: Session, user_id: int, image_id: str) -> bool:
    return (
        db.query(ChatMessage.id)
        .join(ChatSession, ChatMessage.session_id == ChatSession.id)
        .filter(ChatSession.user_id == user_id, ChatMessage.image_id == image_id)
        .first()
        is not None
    )
