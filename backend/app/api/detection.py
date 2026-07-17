"""
目标检测 API 路由 — 上传图片并获取 YOLO 检测结果。
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.session import get_db
from app.entity.db_models import User
from app.entity.schemas import (
    ApiResponse,
    DetectionTaskListResponse,
    DetectionTaskSummary,
    DetectionUploadResponse,
    SceneResponse,
)
from app.services.detection_service import (
    DetectionSceneNotFoundError,
    detection_service,
)

router = APIRouter(prefix="/api/detection", tags=["目标检测"])

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB


# ------------------------------------------------------------------
# 核心检测
# ------------------------------------------------------------------


@router.post("/detect", response_model=ApiResponse)
async def detect_food_image(
    file: UploadFile = File(..., description="JPG/PNG 图片，<=10MB"),
    scene_id: Optional[int] = Form(default=None, description="检测场景 ID；不传时使用首个启用场景"),
    conf_threshold: float = Form(default=0.25, ge=0.0, le=1.0, description="置信度阈值"),
    iou_threshold: float = Form(default=0.45, ge=0.0, le=1.0, description="IoU 阈值"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传图片并执行 YOLO 食物检测。返回检测框和类别信息。"""
    content_type = file.content_type or ""
    if file.filename:
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in ("jpg", "jpeg", "png", "webp"):
            raise HTTPException(status_code=400, detail="仅支持 JPG/PNG/WEBP 格式")

    image_bytes = await file.read()
    if len(image_bytes) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail=f"图片大小超过 {MAX_IMAGE_SIZE // 1024 // 1024}MB")

    if scene_id is None:
        scenes = await detection_service.get_scenes(db)
        if not scenes:
            raise HTTPException(status_code=503, detail="当前没有可用的检测场景")
        scene_id = scenes[0].id

    try:
        result = await detection_service.detect_from_bytes(
            db=db,
            scene_id=scene_id,
            image_bytes=image_bytes,
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
            user_id=current_user.id,
        )
    except DetectionSceneNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return ApiResponse(
        message="检测完成",
        data=DetectionUploadResponse(
            task_id=result.task_id,
            task_uuid=result.task_uuid,
            detections=[d.model_dump() for d in result.detections],
            total_objects=result.total_objects,
            inference_time=result.inference_time,
        ).model_dump(),
    )


# ------------------------------------------------------------------
# 检测场景
# ------------------------------------------------------------------


@router.get("/scenes", response_model=ApiResponse)
async def list_detection_scenes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取所有启用的检测场景列表。"""
    scenes = await detection_service.get_scenes(db)
    return ApiResponse(
        data=[SceneResponse.model_validate(s).model_dump() for s in scenes]
    )


# ------------------------------------------------------------------
# 历史记录查询
# ------------------------------------------------------------------


@router.get("/tasks", response_model=DetectionTaskListResponse)
async def list_detection_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """分页查询历史检测记录。"""
    tasks, total = await detection_service.get_tasks(
        db, user_id=current_user.id, page=page, page_size=page_size
    )
    return DetectionTaskListResponse(
        items=[DetectionTaskSummary.model_validate(t) for t in tasks],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/tasks/{task_uuid}", response_model=ApiResponse)
async def get_detection_task(
    task_uuid: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单条检测记录详情。"""
    task = await detection_service.get_task_by_uuid(db, task_uuid)
    if not task:
        raise HTTPException(status_code=404, detail="检测任务不存在")
    return ApiResponse(data={
        "task_uuid": task.task_uuid,
        "status": task.status,
        "detections": task.detections or [],
        "total_objects": task.total_objects,
        "inference_time": task.inference_time,
        "created_at": task.created_at.isoformat() if task.created_at else None,
    })
