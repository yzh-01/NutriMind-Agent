from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config.settings import settings

# ORM 基类
Base = declarative_base()

# 延迟初始化引擎和会话工厂（支持测试覆盖）
_engine = None
_SessionLocal = None


def get_engine():
    """获取数据库引擎（延迟初始化）"""
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.DATABASE_URL,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=settings.DEBUG,
        )
    return _engine


def get_session_local():
    """获取会话工厂（延迟初始化）"""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal


# 依赖注入函数
def get_db():
    """获取数据库会话（每个请求一个会话，用完自动关闭）"""
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
