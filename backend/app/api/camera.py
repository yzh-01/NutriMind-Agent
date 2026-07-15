"""摄像头 API 路由。"""

import os
import tempfile
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import FileResponse

from app.core.security import get_current_user
from app.entity.db_models import User
from app.entity.schemas import ApiResponse
from app.services.camera_service import camera_service

router = APIRouter(prefix="/api/camera", tags=["摄像头"])

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


@router.post("/capture", response_model=ApiResponse)
async def capture_image(
    file: UploadFile = File(..., description="拍照图片文件"),
    current_user: User = Depends(get_current_user),
):
    """上传拍照图片。

    - **file**: 图片文件（png / jpg / gif / bmp / webp）
    """
    file_ext = os.path.splitext(file.filename or "capture.png")[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型：{file_ext}，支持：{', '.join(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="图片内容为空")

    info = camera_service.save_image(content, file.filename, current_user.id)

    return ApiResponse(
        code=200,
        message="图片上传成功",
        data=info,
    )


@router.get("/list", response_model=ApiResponse)
async def list_images(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
):
    """获取拍照历史列表（分页，按时间倒序）。"""
    result = camera_service.list_images(page=page, page_size=page_size)
    return ApiResponse(code=200, data=result)


@router.get("/view/{image_id}")
async def view_image(
    image_id: str,
    current_user: User = Depends(get_current_user),
):
    """查看/下载指定图片。"""
    path = camera_service.get_image_path(image_id)
    if path is None:
        raise HTTPException(status_code=404, detail="图片不存在")
    return FileResponse(path, media_type="image/png")


@router.delete("/{image_id}", response_model=ApiResponse)
async def delete_image(
    image_id: str,
    current_user: User = Depends(get_current_user),
):
    """删除指定图片。"""
    ok = camera_service.delete_image(image_id)
    if not ok:
        raise HTTPException(status_code=404, detail="图片不存在")
    return ApiResponse(code=200, message="图片已删除")