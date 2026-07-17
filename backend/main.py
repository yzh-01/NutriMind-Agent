from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.camera import router as camera_router
from app.api.chat import router as chat_router
from app.api.detection import router as detection_router
from app.api.training import router as training_router
from app.api.profile import router as profile_router
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.api.knowledge import router as knowledge_router
from app.core.logger import setup_logger, get_logger
from app.middleware.request_logger import RequestLoggerMiddleware
from app.database.seed import init_db, init_seed

# 初始化日志
setup_logger()
logger = get_logger("main")

# 应用生命周期管理


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """启动时执行初始化"""
    init_db()
    init_seed()
    yield
    # 关闭时执行清理

# 创建 FastAPI 实例
app = FastAPI(
    title="NutriMind-Agent",
    version="0.1.0",
    description="基于 YOLOv11 的目标检测智能体平台 API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# 注册 CORS 中间件（必须在其他中间件之前）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册请求日志中间件
app.add_middleware(RequestLoggerMiddleware)

# 注册路由
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(knowledge_router)
app.include_router(dashboard_router)
app.include_router(camera_router)
app.include_router(chat_router)
app.include_router(detection_router)
app.include_router(training_router)
app.include_router(profile_router)


def start():
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=9999, reload=True)


if __name__ == "__main__":
    start()
