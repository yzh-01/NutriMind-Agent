"""
Dashboard 看板路由
提供系统总览、检测统计、训练统计、用户统计等聚合数据接口
"""
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.logger import get_logger
from app.core.security import get_current_user
from app.database.session import get_db
from app.entity.db_models import (
    DetectionScene,
    DetectionTask,
    FoodNutrition,
    TrainingTask,
    User,
)
from app.entity.schemas import (
    ApiResponse,
    DashboardOverview,
    DashboardStats,
    DetectionStats,
    TaskStatusCount,
    TrainingStats,
    UserStats,
)

logger = get_logger("dashboard")

router = APIRouter(prefix="/api/dashboard", tags=["看板"])


# ---------------------------------------------------------------------------
# GET /api/dashboard/overview  — 总览数据
# ---------------------------------------------------------------------------
@router.get("/overview", response_model=ApiResponse)
async def get_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取系统总览数据（需登录）"""
    logger.info(f"用户 {current_user.username} 请求看板总览")

    overview = DashboardOverview(
        total_users=db.query(func.count(User.id)).scalar() or 0,
        active_users=db.query(func.count(User.id)).filter(
            User.is_active.is_(True)).scalar() or 0,
        total_detection_scenes=db.query(
            func.count(DetectionScene.id)).scalar() or 0,
        total_detection_tasks=db.query(
            func.count(DetectionTask.id)).scalar() or 0,
        total_training_tasks=db.query(
            func.count(TrainingTask.id)).scalar() or 0,
        total_food_items=db.query(func.count(FoodNutrition.id)).scalar() or 0,
    )

    return ApiResponse(code=200, message="success", data=overview.model_dump())


# ---------------------------------------------------------------------------
# GET /api/dashboard/detection  — 检测任务统计
# ---------------------------------------------------------------------------
@router.get("/detection", response_model=ApiResponse)
async def get_detection_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取检测任务统计（需登录）"""
    logger.info(f"用户 {current_user.username} 请求检测统计")

    total = db.query(func.count(DetectionTask.id)).scalar() or 0
    completed = db.query(func.count(DetectionTask.id)).filter(
        DetectionTask.status == "completed").scalar() or 0
    failed = db.query(func.count(DetectionTask.id)).filter(
        DetectionTask.status == "failed").scalar() or 0
    pending = db.query(func.count(DetectionTask.id)).filter(
        DetectionTask.status == "pending").scalar() or 0
    processing = db.query(func.count(DetectionTask.id)).filter(
        DetectionTask.status == "processing").scalar() or 0

    total_objects = db.query(func.coalesce(
        func.sum(DetectionTask.total_objects), 0)).scalar() or 0
    avg_time = db.query(func.avg(DetectionTask.inference_time)).filter(
        DetectionTask.inference_time.isnot(None)
    ).scalar()

    stats = DetectionStats(
        total=total,
        completed=completed,
        failed=failed,
        pending=pending,
        processing=processing,
        total_objects_detected=int(total_objects),
        avg_inference_time=round(
            float(avg_time), 4) if avg_time is not None else None,
    )

    return ApiResponse(code=200, message="success", data=stats.model_dump())


# ---------------------------------------------------------------------------
# GET /api/dashboard/training  — 训练任务统计
# ---------------------------------------------------------------------------
@router.get("/training", response_model=ApiResponse)
async def get_training_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取训练任务统计（需登录）"""
    logger.info(f"用户 {current_user.username} 请求训练统计")

    total = db.query(func.count(TrainingTask.id)).scalar() or 0
    completed = db.query(func.count(TrainingTask.id)).filter(
        TrainingTask.status == "completed").scalar() or 0
    failed = db.query(func.count(TrainingTask.id)).filter(
        TrainingTask.status == "failed").scalar() or 0
    running = db.query(func.count(TrainingTask.id)).filter(
        TrainingTask.status == "running").scalar() or 0
    pending = db.query(func.count(TrainingTask.id)).filter(
        TrainingTask.status == "pending").scalar() or 0
    paused = db.query(func.count(TrainingTask.id)).filter(
        TrainingTask.status == "paused").scalar() or 0

    stats = TrainingStats(
        total=total,
        completed=completed,
        failed=failed,
        running=running,
        pending=pending,
        paused=paused,
    )

    return ApiResponse(code=200, message="success", data=stats.model_dump())


# ---------------------------------------------------------------------------
# GET /api/dashboard/users  — 用户统计
# ---------------------------------------------------------------------------
@router.get("/users", response_model=ApiResponse)
async def get_user_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户统计（需登录）"""
    logger.info(f"用户 {current_user.username} 请求用户统计")

    total = db.query(func.count(User.id)).scalar() or 0
    active = db.query(func.count(User.id)).filter(
        User.is_active.is_(True)).scalar() or 0
    superusers = db.query(func.count(User.id)).filter(
        User.is_superuser.is_(True)).scalar() or 0

    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0)
    new_today = db.query(func.count(User.id)).filter(
        User.created_at >= today_start).scalar() or 0

    stats = UserStats(
        total=total,
        active=active,
        superusers=superusers,
        new_today=new_today,
    )

    return ApiResponse(code=200, message="success", data=stats.model_dump())


# ---------------------------------------------------------------------------
# GET /api/dashboard/stats  — 完整看板数据（聚合）
# ---------------------------------------------------------------------------
@router.get("/stats", response_model=ApiResponse)
async def get_full_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取完整看板统计数据（需登录）"""
    logger.info(f"用户 {current_user.username} 请求完整看板统计")

    # --- overview ---
    overview = DashboardOverview(
        total_users=db.query(func.count(User.id)).scalar() or 0,
        active_users=db.query(func.count(User.id)).filter(
            User.is_active.is_(True)).scalar() or 0,
        total_detection_scenes=db.query(
            func.count(DetectionScene.id)).scalar() or 0,
        total_detection_tasks=db.query(
            func.count(DetectionTask.id)).scalar() or 0,
        total_training_tasks=db.query(
            func.count(TrainingTask.id)).scalar() or 0,
        total_food_items=db.query(func.count(FoodNutrition.id)).scalar() or 0,
    )

    # --- detection ---
    det_total = db.query(func.count(DetectionTask.id)).scalar() or 0
    det_completed = db.query(func.count(DetectionTask.id)).filter(
        DetectionTask.status == "completed").scalar() or 0
    det_failed = db.query(func.count(DetectionTask.id)).filter(
        DetectionTask.status == "failed").scalar() or 0
    det_pending = db.query(func.count(DetectionTask.id)).filter(
        DetectionTask.status == "pending").scalar() or 0
    det_processing = db.query(func.count(DetectionTask.id)).filter(
        DetectionTask.status == "processing").scalar() or 0
    det_objects = db.query(func.coalesce(
        func.sum(DetectionTask.total_objects), 0)).scalar() or 0
    det_avg_time = db.query(func.avg(DetectionTask.inference_time)).filter(
        DetectionTask.inference_time.isnot(None)
    ).scalar()

    detection = DetectionStats(
        total=det_total,
        completed=det_completed,
        failed=det_failed,
        pending=det_pending,
        processing=det_processing,
        total_objects_detected=int(det_objects),
        avg_inference_time=round(
            float(det_avg_time), 4) if det_avg_time is not None else None,
    )

    # --- training ---
    tr_total = db.query(func.count(TrainingTask.id)).scalar() or 0
    tr_completed = db.query(func.count(TrainingTask.id)).filter(
        TrainingTask.status == "completed").scalar() or 0
    tr_failed = db.query(func.count(TrainingTask.id)).filter(
        TrainingTask.status == "failed").scalar() or 0
    tr_running = db.query(func.count(TrainingTask.id)).filter(
        TrainingTask.status == "running").scalar() or 0
    tr_pending = db.query(func.count(TrainingTask.id)).filter(
        TrainingTask.status == "pending").scalar() or 0
    tr_paused = db.query(func.count(TrainingTask.id)).filter(
        TrainingTask.status == "paused").scalar() or 0

    training = TrainingStats(
        total=tr_total,
        completed=tr_completed,
        failed=tr_failed,
        running=tr_running,
        pending=tr_pending,
        paused=tr_paused,
    )

    # --- users ---
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0)
    users = UserStats(
        total=overview.total_users,
        active=overview.active_users,
        superusers=db.query(func.count(User.id)).filter(
            User.is_superuser.is_(True)).scalar() or 0,
        new_today=db.query(func.count(User.id)).filter(
            User.created_at >= today_start).scalar() or 0,
    )

    stats = DashboardStats(
        overview=overview,
        detection=detection,
        training=training,
        users=users,
    )

    return ApiResponse(code=200, message="success", data=stats.model_dump())


# ---------------------------------------------------------------------------
# GET /api/dashboard/detection/status-distribution  — 检测任务状态分布
# ---------------------------------------------------------------------------
@router.get("/detection/status-distribution", response_model=ApiResponse)
async def get_detection_status_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取检测任务各状态数量分布（需登录）"""
    logger.info(f"用户 {current_user.username} 请求检测状态分布")

    rows = (
        db.query(DetectionTask.status, func.count(DetectionTask.id))
        .group_by(DetectionTask.status)
        .all()
    )

    distribution: List[TaskStatusCount] = [
        TaskStatusCount(status=str(row[0] or "unknown"), count=row[1])
        for row in rows
    ]

    return ApiResponse(
        code=200,
        message="success",
        data=[item.model_dump() for item in distribution],
    )


# ---------------------------------------------------------------------------
# GET /api/dashboard/training/status-distribution  — 训练任务状态分布
# ---------------------------------------------------------------------------
@router.get("/training/status-distribution", response_model=ApiResponse)
async def get_training_status_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取训练任务各状态数量分布（需登录）"""
    logger.info(f"用户 {current_user.username} 请求训练状态分布")

    rows = (
        db.query(TrainingTask.status, func.count(TrainingTask.id))
        .group_by(TrainingTask.status)
        .all()
    )

    distribution: List[TaskStatusCount] = [
        TaskStatusCount(status=str(row[0] or "unknown"), count=row[1])
        for row in rows
    ]

    return ApiResponse(
        code=200,
        message="success",
        data=[item.model_dump() for item in distribution],
    )
