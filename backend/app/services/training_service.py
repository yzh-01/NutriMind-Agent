"""
训练服务模块 — YOLOv11 模型微调任务管理与后台训练执行。

职责：
- 训练任务的创建、启动、暂停（CRUD 生命周期管理）
- 后台异步训练执行（asyncio.create_task 拉起，不阻塞请求响应）
- 训练指标（mAP、Precision、Recall、Loss）的记录与状态回写
- 借助 YOLOv11 特有的 MuSGD 优化器保障训练稳定性

注意：
- 训练是 CPU/GPU 密集型操作，必须在 asyncio.to_thread() 中执行
- 每次训练使用独立的数据库会话，避免长事务问题
"""

import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.database.session import get_session_local
from app.entity.db_models import TrainingTask
from app.entity.schemas import TrainingTaskCreate


class TrainingService:
    """YOLOv11 训练服务 — 管理模型微调任务。"""

    # ------------------------------------------------------------------
    # 任务生命周期管理
    # ------------------------------------------------------------------

    async def create_task(
        self,
        db: Session,
        config: TrainingTaskCreate,
        user_id: Optional[int] = None,
    ) -> TrainingTask:
        """创建训练任务（状态 = pending），不立即执行。

        Args:
            db: 数据库会话
            config: 训练请求参数（模型名、data.yaml、epochs 等）
            user_id: 创建者用户 ID

        Returns:
            已持久化的 TrainingTask ORM 对象
        """
        task = TrainingTask(
            user_id=user_id,
            scene_id=config.scene_id,
            task_uuid=str(uuid.uuid4()),
            model_name=config.model_name,
            data_yaml=config.data_yaml,
            epochs=config.epochs,
            img_size=config.img_size,
            batch_size=config.batch_size,
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    async def start_task(
        self, db: Session, task_uuid: str
    ) -> TrainingTask:
        """启动训练任务 — 校验状态后拉起后台训练协程。

        使用 asyncio.create_task 将训练放入后台执行，
        方法立即返回，不等待训练完成。

        Args:
            db: 数据库会话
            task_uuid: 要启动的任务 UUID

        Returns:
            更新后的 TrainingTask（status = running）

        Raises:
            ValueError: 任务状态不允许启动（非 pending 状态）
        """
        task = db.query(TrainingTask).filter(
            TrainingTask.task_uuid == task_uuid
        ).first()

        if task is None:
            raise ValueError(f"训练任务不存在: {task_uuid}")

        if task.status != "pending":
            raise ValueError(
                f"无法启动状态为 '{task.status}' 的任务，仅允许启动 pending 状态的任务"
            )

        # 标记为 running
        task.status = "running"
        task.started_at = datetime.now()
        db.commit()

        # 后台拉起训练（不等待完成）
        asyncio.create_task(self._run_training(task_uuid))

        db.refresh(task)
        return task

    async def pause_task(
        self, db: Session, task_uuid: str
    ) -> TrainingTask:
        """暂停训练任务。

        注意：ultralytics 库本身不支持优雅暂停运行中的训练，
        此方法主要用于标记数据库状态以传达用户意图。

        Args:
            db: 数据库会话
            task_uuid: 任务 UUID

        Returns:
            更新后的 TrainingTask
        """
        task = db.query(TrainingTask).filter(
            TrainingTask.task_uuid == task_uuid
        ).first()

        if task is None:
            raise ValueError(f"训练任务不存在: {task_uuid}")

        if task.status != "running":
            raise ValueError(f"无法暂停状态为 '{task.status}' 的任务")

        task.status = "paused"
        db.commit()
        db.refresh(task)
        return task

    # ------------------------------------------------------------------
    # 后台训练执行（核心）
    # ------------------------------------------------------------------

    async def _run_training(self, task_uuid: str) -> None:
        """后台执行 YOLOv11 模型训练（内部方法）。

        针对 AutoDL 环境 (RTX 3080 Ti / 12GB VRAM / 90GB RAM) 深度优化：
        1. 使用独立的数据库会话（避免长事务）
        2. YOLO.train() 通过 asyncio.to_thread 放入线程池
        3. 缓存全量图片到 RAM（利用 90GB 大内存）
        4. 自动混合精度 AMP 节省显存
        5. OOM 时自动降级 batch size 重试
        6. 训练结束后自动将 best.pt 复制到 data/models/

        Args:
            task_uuid: 要执行训练的任务 UUID
        """
        db: Optional[Session] = None
        try:
            # 独立会话
            db = get_session_local()()
            task = db.query(TrainingTask).filter(
                TrainingTask.task_uuid == task_uuid
            ).first()

            if task is None:
                return

            # 验证 data.yaml 存在
            data_yaml_path = Path(task.data_yaml)
            if not data_yaml_path.is_absolute():
                data_yaml_path = settings.BASE_DIR / data_yaml_path
            if not data_yaml_path.exists():
                raise FileNotFoundError(
                    f"数据集配置文件不存在: {data_yaml_path}"
                )

            # 预训练权重路径
            base_model = f"{task.model_name}.pt"
            base_model_path = settings.MODELS_DIR / base_model

            # 实例化 YOLOv11 并执行训练
            from ultralytics import YOLO

            model_path = str(
                base_model_path) if base_model_path.exists() else base_model

            # 自动 batch size 降级列表
            batch_sizes = [task.batch_size] + [
                b for b in [32, 24, 16, 12, 8, 4, 2] if b < task.batch_size
            ]

            train_results = None
            last_error = None

            for bs in batch_sizes:
                try:
                    def _train_sync() -> dict:
                        """同步训练函数，在线程池中执行。"""
                        model = YOLO(model_path)
                        results = model.train(
                            data=str(data_yaml_path),
                            epochs=task.epochs,
                            imgsz=task.img_size,
                            batch=bs,
                            workers=8,           # 12 核 CPU 用 8 线程加载数据
                            patience=10,         # 10 轮无提升自动早停
                            cache="ram",         # 90GB 内存全量缓存图片
                            amp=True,            # 自动混合精度（省显存+加速）
                            device=0,            # GPU 0
                            exist_ok=True,
                            pretrained=True,
                            verbose=True,
                            # 轻量数据增强（密集检测友好）
                            hsv_h=0.015,
                            hsv_s=0.7,
                            hsv_v=0.4,
                            degrees=5.0,
                            translate=0.1,
                            scale=0.3,
                            mosaic=0.5,
                            mixup=0.1,
                        )
                        return results

                    train_results = await asyncio.to_thread(_train_sync)
                    break  # 训练成功，退出重试循环

                except RuntimeError as e:
                    last_error = e
                    error_msg = str(e)
                    if "out of memory" in error_msg.lower() or "OOM" in error_msg:
                        if bs > batch_sizes[-1]:
                            continue  # 降级重试
                    raise  # 非 OOM 错误，直接抛出

            if train_results is None:
                raise RuntimeError(
                    f"训练失败：所有 batch size ({batch_sizes}) 均 OOM。"
                    f"最后错误: {last_error}"
                )

            # ultralytics 训练结果中包含多种指标，优先取最佳 epoch 的结果
            metrics = {
                "mAP50": (
                    float(train_results.results_dict.get("metrics/mAP50(B)", 0))
                    if hasattr(train_results, "results_dict")
                    else None
                ),
                "mAP50-95": (
                    float(train_results.results_dict.get(
                        "metrics/mAP50-95(B)", 0))
                    if hasattr(train_results, "results_dict")
                    else None
                ),
                "precision": (
                    float(train_results.results_dict.get(
                        "metrics/precision(B)", 0))
                    if hasattr(train_results, "results_dict")
                    else None
                ),
                "recall": (
                    float(train_results.results_dict.get(
                        "metrics/recall(B)", 0))
                    if hasattr(train_results, "results_dict")
                    else None
                ),
                "box_loss": (
                    float(train_results.results_dict.get("train/box_loss", 0))
                    if hasattr(train_results, "results_dict")
                    else None
                ),
                "cls_loss": (
                    float(train_results.results_dict.get("train/cls_loss", 0))
                    if hasattr(train_results, "results_dict")
                    else None
                ),
            }

            # 确定输出模型路径
            output_model_path = str(
                settings.MODELS_DIR / f"{task.task_uuid}_best.pt"
            )

            # 从训练输出目录复制 best.pt
            import shutil

            save_dir = getattr(train_results, "save_dir", None)
            if save_dir:
                src_best = Path(save_dir) / "weights" / "best.pt"
                if src_best.exists():
                    shutil.copy2(str(src_best), output_model_path)
                    # 同时复制一份为通用名（方便检测服务直接使用）
                    generic_path = settings.MODELS_DIR / "yolo11_food_best.pt"
                    shutil.copy2(str(src_best), str(generic_path))

            # 更新任务状态 → completed
            task.status = "completed"
            task.metrics = metrics
            task.batch_size = batch_sizes[0] if train_results else task.batch_size
            task.progress = 100.0
            task.output_model_path = output_model_path
            task.completed_at = datetime.now()
            db.commit()

        except Exception as exc:
            if db is not None:
                task = db.query(TrainingTask).filter(
                    TrainingTask.task_uuid == task_uuid
                ).first()
                if task:
                    task.status = "failed"
                    task.error_message = str(exc)
                    db.commit()
            raise
        finally:
            if db is not None:
                db.close()

    # ------------------------------------------------------------------
    # 查询方法
    # ------------------------------------------------------------------

    async def get_tasks(
        self,
        db: Session,
        user_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[TrainingTask], int]:
        """分页查询训练任务。

        Args:
            db: 数据库会话
            user_id: 按用户筛选
            page: 页码
            page_size: 每页条数

        Returns:
            (任务列表, 总数)
        """
        query = db.query(TrainingTask)
        if user_id is not None:
            query = query.filter(TrainingTask.user_id == user_id)

        total = query.count()
        tasks = (
            query.order_by(TrainingTask.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return tasks, total

    async def get_task_by_uuid(
        self, db: Session, task_uuid: str
    ) -> Optional[TrainingTask]:
        """按 UUID 查询单个训练任务。"""
        return (
            db.query(TrainingTask)
            .filter(TrainingTask.task_uuid == task_uuid)
            .first()
        )

    async def get_models(self) -> list[dict]:
        """扫描 data/models/ 目录，获取已有模型文件列表。

        Returns:
            模型文件信息列表 [{"name": ..., "path": ..., "size_bytes": ..., "created_at": ...}]
        """
        models_dir = settings.MODELS_DIR
        if not models_dir.exists():
            return []

        models = []
        for pt_file in models_dir.glob("*.pt"):
            stat = pt_file.stat()
            models.append(
                {
                    "name": pt_file.name,
                    "path": str(pt_file.absolute()),
                    "size_bytes": stat.st_size,
                    "created_at": datetime.fromtimestamp(stat.st_ctime),
                }
            )
        return sorted(models, key=lambda m: m["created_at"], reverse=True)

    async def delete_model(self, model_name: str) -> bool:
        """删除指定模型文件。

        Args:
            model_name: 模型文件名（不含路径）

        Returns:
            是否成功删除
        """
        model_path = settings.MODELS_DIR / model_name
        if model_path.exists():
            model_path.unlink()
            # 同时清除 DetectionService 中的模型缓存
            from app.services.detection_service import detection_service
            await detection_service.unload_model(str(model_path))
            return True
        return False


def _extract_training_metrics(train_results) -> dict:
    """从 ultralytics 训练结果中提取关键指标。

    Args:
        train_results: YOLO.train() 的返回结果

    Returns:
        包含 mAP、Precision、Recall、Loss 的指标字典
    """
    metrics = {}
    if hasattr(train_results, "results_dict"):
        rd = train_results.results_dict
        metrics["mAP50"] = float(rd.get("metrics/mAP50(B)", 0))
        metrics["mAP50-95"] = float(rd.get("metrics/mAP50-95(B)", 0))
        metrics["precision"] = float(rd.get("metrics/precision(B)", 0))
        metrics["recall"] = float(rd.get("metrics/recall(B)", 0))
        metrics["box_loss"] = float(rd.get("train/box_loss", 0))
        metrics["cls_loss"] = float(rd.get("train/cls_loss", 0))
    return metrics


# 模块级单例
training_service = TrainingService()
