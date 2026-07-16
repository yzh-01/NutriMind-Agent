"""健康检查路由。"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/health", tags=["健康检查"])


@router.get("")
async def health_check():
    """健康检查。"""
    return {"status": "ok", "message": "NutriMind-Agent API is running"}