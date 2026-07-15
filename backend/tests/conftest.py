"""
测试配置文件
- 使用 SQLite 内存数据库替代 PostgreSQL
- 提供 FastAPI TestClient 和数据库会话 fixture
"""
from main import app
from app.database.session import Base
import app.database.session as session_module
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# ── 在导入应用模块之前，设置测试环境变量 ──
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

# ── 测试数据库引擎 ────────────────────────────────
TEST_DATABASE_URL = "sqlite:///./test.db"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=test_engine)

# 在导入 app 模块之前，预先注入测试引擎到 session 模块
session_module._engine = test_engine
session_module._SessionLocal = TestSessionLocal


@pytest.fixture(scope="function")
def db():
    """每个测试函数独立的数据库会话"""
    Base.metadata.create_all(bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient"""
    with TestClient(app) as c:
        yield c
