"""
检测服务模块 — YOLOv11 模型加载、图片推理与结果解析。

职责：
- 模型单例缓存，防止每次请求重复加载导致 OOM
- 异步执行 YOLOv11 推理（通过 asyncio.to_thread 避免阻塞事件循环）
- 解析推理结果为标准 DetectionResponse Schema
- 持久化检测记录到数据库
"""

import asyncio
import time
import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.config.settings import settings
from app.entity.db_models import DetectionScene, DetectionTask
from app.entity.schemas import BoundingBox, DetectionResponse


class DetectionService:
    """YOLOv11 检测服务 — 管理模型加载与图片推理。"""

    def __init__(self) -> None:
        # 模型缓存字典：{model_path: YOLO_instance}
        # 使用字典而非单值，支持多场景加载不同模型
        self.models: dict[str, object] = {}

    # ------------------------------------------------------------------
    # 模型加载与缓存
    # ------------------------------------------------------------------

    async def _load_model(self, model_path: str) -> object:
        """异步加载 YOLOv11 模型（通过 asyncio.to_thread 避免阻塞事件循环）。

        Args:
            model_path: 模型权重文件路径（如 data/models/best.pt）

        Returns:
            已加载的 YOLO 模型实例
        """
        if model_path not in self.models:
            from ultralytics import YOLO

            loop = asyncio.get_running_loop()
            # YOLO 构造函数涉及磁盘 I/O（读取 .pt 文件），放到线程池执行
            self.models[model_path] = await loop.run_in_executor(
                None, YOLO, model_path
            )
        return self.models[model_path]

    async def _get_or_load_model(self, model_path: str) -> object:
        """获取已缓存的模型，未命中则加载并缓存。

        Args:
            model_path: 模型文件路径

        Returns:
            YOLO 模型实例
        """
        if model_path not in self.models:
            return await self._load_model(model_path)
        return self.models[model_path]

    async def unload_model(self, model_path: str) -> None:
        """卸载指定模型以释放内存。

        Args:
            model_path: 要卸载的模型路径
        """
        if model_path in self.models:
            del self.models[model_path]

    async def unload_all_models(self) -> None:
        """卸载所有已缓存模型。"""
        self.models.clear()

    # ------------------------------------------------------------------
    # 模型路径解析
    # ------------------------------------------------------------------

    async def _resolve_model_path(
        self, db: Session, scene_id: int
    ) -> str:
        """根据场景 ID 解析模型文件路径。

        优先级：场景配置的 model_path > 全局 DEFAULT_MODEL_PATH

        Args:
            db: 数据库会话
            scene_id: 检测场景 ID

        Returns:
            模型文件的绝对路径
        """
        # 查询场景配置
        scene = db.query(DetectionScene).filter(
            DetectionScene.id == scene_id,
            DetectionScene.is_active == True,
        ).first()

        if scene and scene.model_path:
            model_path = Path(scene.model_path)
        else:
            # 回退到全局默认模型路径
            model_path = settings.MODELS_DIR / "yolo11_food_best.pt"

        # 确保路径为绝对路径
        if not model_path.is_absolute():
            model_path = settings.BASE_DIR / model_path

        return str(model_path.resolve())

    async def _validate_model_exists(self, model_path: str) -> None:
        """验证模型文件是否存在。

        Args:
            model_path: 模型文件路径

        Raises:
            FileNotFoundError: 模型文件不存在时抛出
        """
        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(
                f"模型文件不存在: {model_path}。请确保已完成 Phase 1.3（将 best.pt 放入 data/models/ 目录）"
            )

    # ------------------------------------------------------------------
    # 推理结果解析
    # ------------------------------------------------------------------

    def _parse_yolo_results(
        self, results, db: Session, scene_id: int
    ) -> tuple[list[BoundingBox], int]:
        """解析 YOLOv11 推理结果，提取检测框信息。

        Args:
            results: ultralytics YOLO.predict() 的返回结果
            db: 数据库会话（用于查询类名映射）
            scene_id: 场景 ID

        Returns:
            (detections 列表, 目标总数)
        """
        # 获取场景的中文类名映射
        scene = db.query(DetectionScene).filter(
            DetectionScene.id == scene_id
        ).first()
        class_names_cn: dict[int, str] = {}
        if scene and scene.class_names_cn:
            # class_names_cn 是个 list，索引对应 class_id
            for i, name in enumerate(scene.class_names_cn):
                class_names_cn[i] = name

        detections: list[BoundingBox] = []
        result = results[0]

        if result.boxes is None:
            return detections, 0

        for box in result.boxes:
            class_id = int(box.cls[0])
            class_name = result.names[class_id] if result.names else str(class_id)
            confidence = float(box.conf[0])
            bbox_values = box.xyxy[0].tolist()  # [x1, y1, x2, y2]

            detection = BoundingBox(
                class_name=class_name,
                class_name_cn=class_names_cn.get(class_id),
                confidence=round(confidence, 4),
                bbox=[round(v, 2) for v in bbox_values],
            )
            detections.append(detection)

        return detections, len(detections)

    # ------------------------------------------------------------------
    # 核心推理方法
    # ------------------------------------------------------------------

    async def detect_from_path(
        self,
        db: Session,
        scene_id: int,
        image_path: str,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        user_id: Optional[int] = None,
    ) -> DetectionResponse:
        """从本地图片路径执行 YOLOv11 检测。

        这是检测服务的核心方法，负责完整的：
        1. 模型加载（缓存命中/未命中）
        2. 异步推理（线程池隔离）
        3. 结果解析
        4. 数据库记录持久化

        Args:
            db: 数据库会话
            scene_id: 检测场景 ID
            image_path: 待检测图片的本地路径
            conf_threshold: 置信度阈值（0-1）
            iou_threshold: IoU 阈值（0-1）
            user_id: 提交用户 ID（可选）

        Returns:
            DetectionResponse: 包含所有检测框信息与推理耗时
        """
        task_uuid_str = str(uuid.uuid4())
        start_time = time.perf_counter()

        # 1. 创建任务记录（pending 状态）
        task = DetectionTask(
            user_id=user_id,
            scene_id=scene_id,
            task_uuid=task_uuid_str,
            image_path=image_path,
            status="processing",
            conf_threshold=conf_threshold,
            iou_threshold=iou_threshold,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        try:
            # 2. 解析并验证模型路径
            model_path = await self._resolve_model_path(db, scene_id)
            await self._validate_model_exists(model_path)

            # 3. 加载模型（命中缓存则即时返回）
            model = await self._get_or_load_model(model_path)

            # 4. 执行推理 —— 关键！YOLO.predict 是同步阻塞的 CPU/GPU 操作，
            #    必须通过 asyncio.to_thread 放入线程池，防止阻塞 FastAPI 事件循环
            results = await asyncio.to_thread(
                model.predict,
                source=image_path,
                conf=conf_threshold,
                iou=iou_threshold,
                verbose=False,
            )

            # 5. 解析结果
            detections, total_objects = self._parse_yolo_results(
                results, db, scene_id
            )
            inference_time = round(time.perf_counter() - start_time, 4)

            # 6. 更新任务记录为 completed
            task.status = "completed"
            task.detections = [d.model_dump() for d in detections]
            task.total_objects = total_objects
            task.inference_time = inference_time
            db.commit()
            db.refresh(task)

            return DetectionResponse(
                task_id=task.id,
                task_uuid=task.task_uuid,
                detections=detections,
                total_objects=total_objects,
                inference_time=inference_time,
                image_url=task.image_url,
                created_at=task.created_at,
            )

        except Exception as exc:
            # 推理失败 — 记录错误信息
            task.status = "failed"
            task.error_message = str(exc)
            db.commit()
            raise

    async def detect_from_bytes(
        self,
        db: Session,
        scene_id: int,
        image_bytes: bytes,
        conf_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        user_id: Optional[int] = None,
    ) -> DetectionResponse:
        """从图片字节流执行 YOLOv11 检测。

        先将字节流写入临时文件，然后调用 detect_from_path。
        使用完毕后自动清理临时文件。

        Args:
            db: 数据库会话
            scene_id: 检测场景 ID
            image_bytes: 图片字节流
            conf_threshold: 置信度阈值
            iou_threshold: IoU 阈值
            user_id: 用户 ID

        Returns:
            DetectionResponse
        """
        import tempfile

        import aiofiles

        # 写入临时文件
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            async with aiofiles.open(tmp_path, "wb") as f:
                await f.write(image_bytes)

            result = await self.detect_from_path(
                db=db,
                scene_id=scene_id,
                image_path=tmp_path,
                conf_threshold=conf_threshold,
                iou_threshold=iou_threshold,
                user_id=user_id,
            )
            return result

        finally:
            # 清理临时文件
            Path(tmp_path).unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # 查询方法
    # ------------------------------------------------------------------

    async def get_scenes(self, db: Session) -> list[DetectionScene]:
        """获取所有启用的检测场景列表。

        Args:
            db: 数据库会话

        Returns:
            场景 ORM 对象列表
        """
        return (
            db.query(DetectionScene)
            .filter(DetectionScene.is_active == True)
            .order_by(DetectionScene.id)
            .all()
        )

    async def get_tasks(
        self,
        db: Session,
        user_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[DetectionTask], int]:
        """分页查询检测任务记录。

        Args:
            db: 数据库会话
            user_id: 按用户筛选（可选，None 查全部）
            page: 页码（从 1 开始）
            page_size: 每页条数

        Returns:
            (任务列表, 总数)
        """
        query = db.query(DetectionTask)
        if user_id is not None:
            query = query.filter(DetectionTask.user_id == user_id)

        total = query.count()
        tasks = (
            query.order_by(DetectionTask.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return tasks, total

    async def get_task_by_uuid(
        self, db: Session, task_uuid: str
    ) -> Optional[DetectionTask]:
        """按 UUID 查询单个检测任务。

        Args:
            db: 数据库会话
            task_uuid: 任务唯一标识

        Returns:
            DetectionTask 或 None
        """
        return (
            db.query(DetectionTask)
            .filter(DetectionTask.task_uuid == task_uuid)
            .first()
        )


# 模块级单例 — 整个应用共享同一个 DetectionService 实例
detection_service = DetectionService()
