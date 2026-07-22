"""用户个人资料与身体目标 API。"""
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.session import get_db
from app.entity.db_models import User
from app.entity.schemas import ApiResponse
from app.services.profile_service import profile_service
from app.services.avatar_service import avatar_service

router = APIRouter(prefix="/api/users/me", tags=["个人资料"])

AVATAR_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_AVATAR = 5 * 1024 * 1024  # 5MB


@router.get("/profile", response_model=ApiResponse)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户完整个人资料（account + body_profile + goal）。
    未配置部分返回 null，不返回 404。
    """
    data = profile_service.get_profile(db, current_user)
    return ApiResponse(code=200, message="success", data=data)


@router.patch("/profile", response_model=ApiResponse)
async def update_profile(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """部分更新个人资料（支持首次创建 upsert）。
    - 显式传 null 清空字段
    - 未传字段保持不变
    """
    try:
        data = profile_service.update_profile(db, current_user, body)
        db.commit()
        return ApiResponse(code=200, message="个人资料已更新", data=data)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="更新失败")


@router.post("/avatar", response_model=ApiResponse)
async def upload_avatar(
    file: UploadFile = File(..., description="头像文件 (jpg/png/webp, ≤5MB)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传或替换头像。"""
    ext = os.path.splitext(file.filename or "avatar.png")[1].lower()
    if ext not in AVATAR_EXTS:
        raise HTTPException(status_code=415, detail=f"不支持的文件类型: {ext}")

    content = await file.read()
    if len(content) > MAX_AVATAR:
        raise HTTPException(status_code=413, detail="头像不能超过 5MB")
    if not content:
        raise HTTPException(status_code=400, detail="文件为空")

    url = avatar_service.save(content, current_user.id)
    current_user.avatar = url
    db.commit()

    return ApiResponse(code=200, message="头像已更新",
                       data={"avatar": url, "updated_at": None})


@router.delete("/avatar", response_model=ApiResponse)
async def delete_avatar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """移除头像。"""
    avatar_service.delete(current_user.id)
    current_user.avatar = None
    db.commit()
    return ApiResponse(code=200, message="头像已移除", data={"avatar": None})


@router.get("/avatar/file/{image_id}")
async def view_avatar(
    image_id: str,
    current_user: User = Depends(get_current_user),
):
    """查看头像图片。"""
    try:
        uid = int(image_id.replace(".png", ""))
    except ValueError:
        raise HTTPException(status_code=404, detail="头像不存在")
    path = avatar_service.get_path(uid)
    if path is None:
        raise HTTPException(status_code=404, detail="头像不存在")
    return FileResponse(path, media_type="image/png")