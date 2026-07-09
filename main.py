from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config.settings import settings

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
    title="XJTU—VisAgent",
    version="0.1.0",
    description="基于 YOLOv11 的目标检测智能体平台 API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# 注册路由
# app.include_router(auth_router)
# app.include_router(health_router)
# app.include_router(training_router)
# app.include_router(detection_router)
# app.include_router(chat_router)
# app.include_router(dashboard_router)
# app.include_router(camera_router)
# app.include_router(knowledge_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8888,
        reload=True,
    )