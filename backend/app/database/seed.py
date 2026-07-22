"""数据库初始化：建表与幂等种子数据。"""

import logging

from sqlalchemy import inspect, text

from app.database.session import Base, get_engine, get_session_local
from app.entity.db_models import DetectionScene


logger = logging.getLogger(__name__)


DEFAULT_DETECTION_SCENE = {
    "name": "food_detection",
    "display_name": "食物检测（默认）",
    "category": "food",
    # 实际类别名读取自 YOLO 权重，避免在数据库中维护一份容易过期的副本。
    "class_names": [],
    "model_path": "data/models/yolo11_food_best.pt",
    "conf_threshold": 0.25,
    "iou_threshold": 0.45,
    "is_active": True,
    "description": "UECFOOD-256 训练的 YOLO11s 食物检测模型",
}


def init_db() -> None:
    """创建所有尚不存在的 ORM 数据表。"""
    engine = get_engine()
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    needed = set(Base.metadata.tables.keys())
    if needed - existing:
        logger.info("创建数据库表: %s", sorted(needed - existing))
    Base.metadata.create_all(bind=engine)
    # create_all 不会给已有表补列；为历史部署执行安全、幂等的增量升级。
    inspector = inspect(engine)
    if "chat_messages" in inspector.get_table_names():
        columns = {column["name"] for column in inspector.get_columns("chat_messages")}
        if "image_id" not in columns:
            logger.info("升级 chat_messages：添加 image_id 列")
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE chat_messages ADD COLUMN image_id VARCHAR(64)"))


def init_seed() -> None:
    """幂等创建默认食物检测场景。"""
    db = get_session_local()()
    try:
        scene = (
            db.query(DetectionScene)
            .filter(DetectionScene.name == DEFAULT_DETECTION_SCENE["name"])
            .first()
        )
        if scene is None:
            db.add(DetectionScene(**DEFAULT_DETECTION_SCENE))
            db.commit()
            logger.info("已创建默认检测场景: %s", DEFAULT_DETECTION_SCENE["name"])
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
