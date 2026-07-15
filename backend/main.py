from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config.settings import settings
from app.api.knowledge import router as knowledge_router
from app.core.logger import setup_logger, get_logger
from app.middleware.request_logger import RequestLoggerMiddleware

# 初始化日志
setup_logger()
logger = get_logger("main")

# 应用生命周期管理


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """启动时执行初始化"""
    # # 1. 初始化 MinIO 存储桶
    # init_minio()
    # # 2. 初始化 Redis 连接
    # init_redis()
    # # 3. 初始化数据库表和种子数据
    # init_seed()
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

# 注册请求日志中间件
app.add_middleware(RequestLoggerMiddleware)

# 注册路由 - 只启用认证和健康检查用于测试

app.include_router(auth_router)
app.include_router(health_router)
app.include_router(knowledge_router)
app.include_router(dashboard_router)


def start():
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=9999, reload=True)


if __name__ == "__main__":
    start()
