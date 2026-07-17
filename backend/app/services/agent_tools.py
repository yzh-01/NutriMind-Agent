"""
Agent 工具函数模块 — 为 LLM Agent 提供可调用的 Python 工具。

职责：
- 查询食物营养数据（query_food_calories）
- 按类别浏览食物（query_food_by_category）
- 计算总营养摄入（calculate_total_nutrition）
- 获取用户健康档案（get_user_profile）
- 保存检测记录（save_detection_record）

每个工具都使用 @tool 装饰器，LangChain/LangGraph 框架可直接调用。
所有数据库操作使用独立的同步会话，在 async 上下文中通过 asyncio.to_thread 包装。
"""

import asyncio
import base64
import json
import logging
from pathlib import Path
from sqlalchemy.exc import SQLAlchemyError
from app.config.settings import settings
from app.database.session import get_session_local
from app.entity.db_models import DetectionScene, DetectionTask, FoodNutrition, User
from app.services.image_store import image_store

logger = logging.getLogger(__name__)
_yolo_model = None
_vision_llm = None


def SessionLocal():
    """兼容旧调用方式，同时保留 main 分支的延迟数据库初始化。"""
    return get_session_local()()

# 模型联调阶段的内置演示数据。数据库可用时优先使用数据库；数据库未初始化时，
# 常见食物仍可完成 YOLO JSON → 营养计算 → Agent 建议的端到端验证。
BUILTIN_NUTRITION = {
    "apple": {"cn": "苹果", "calories": 52, "protein": 0.3, "fat": 0.2, "carbs": 13.8, "fiber": 2.4, "category": "fruit"},
    "banana": {"cn": "香蕉", "calories": 89, "protein": 1.1, "fat": 0.3, "carbs": 22.8, "fiber": 2.6, "category": "fruit"},
    "rice": {"cn": "米饭", "calories": 116, "protein": 2.6, "fat": 0.3, "carbs": 25.9, "fiber": 0.3, "category": "staple"},
    "chicken": {"cn": "鸡肉", "calories": 165, "protein": 31.0, "fat": 3.6, "carbs": 0.0, "fiber": 0.0, "category": "meat"},
    "beef": {"cn": "牛肉", "calories": 250, "protein": 26.0, "fat": 15.0, "carbs": 0.0, "fiber": 0.0, "category": "meat"},
    "egg": {"cn": "鸡蛋", "calories": 143, "protein": 12.6, "fat": 9.5, "carbs": 0.7, "fiber": 0.0, "category": "protein"},
    "broccoli": {"cn": "西兰花", "calories": 34, "protein": 2.8, "fat": 0.4, "carbs": 6.6, "fiber": 2.6, "category": "vegetable"},
    "tomato": {"cn": "番茄", "calories": 18, "protein": 0.9, "fat": 0.2, "carbs": 3.9, "fiber": 1.2, "category": "vegetable"},
}


def _builtin_food(food_name: str):
    normalized = food_name.strip().lower()
    if normalized in BUILTIN_NUTRITION:
        return normalized, BUILTIN_NUTRITION[normalized]
    for name, data in BUILTIN_NUTRITION.items():
        if food_name.strip() == data["cn"]:
            return name, data
    return None


def _food_values(food) -> dict:
    if isinstance(food, tuple):
        name, data = food
        return {"name": name, **data, "source": "系统内置演示数据"}
    return {
        "name": food.food_name,
        "cn": food.food_name_cn,
        "calories": food.calories_per_100g,
        "protein": food.protein_per_100g,
        "fat": food.fat_per_100g,
        "carbs": food.carbs_per_100g,
        "fiber": food.fiber_per_100g,
        "category": food.category or "未分类",
        "source": food.source or "数据库",
    }


# ==================================================================
# 工具 0：YOLO 食物检测（Agent 的视觉工具）
# ==================================================================

async def detect_food(image_id: str, conf_threshold: float = 0.1) -> str:
    """根据 image_id 调用 YOLO 食物检测，并返回标准 detections JSON。

    识别阈值默认 0.1（低阈值，避免漏检）。confidence < 0.25 的检测结果会标记
    low_confidence=True，Agent 可据此决定是否调用 vision_verify_food 二次确认。

    如果 YOLO 模式未启用或模型不存在，返回 error 提示 Agent 使用视觉兜底。
    """
    try:
        image_path = image_store.get_path(image_id)
        mock_detections = image_store.get_mock_detections(image_id)
        if mock_detections is not None:
            return json.dumps(
                {
                    "success": True,
                    "mode": "mock",
                    "image_id": image_id,
                    "detections": mock_detections,
                    "total_objects": len(mock_detections),
                },
                ensure_ascii=False,
            )

        if settings.DETECTION_MODE != "yolo":
            return json.dumps(
                {
                    "success": False,
                    "mode": settings.DETECTION_MODE,
                    "error": "YOLO 模式未启用",
                    "hint": "请调用 vision_verify_food(image_id) 进行视觉识别兜底",
                },
                ensure_ascii=False,
            )

        model_path = settings.MODELS_DIR / settings.DEFAULT_DETECTION_MODEL
        if not model_path.exists():
            return json.dumps(
                {
                    "success": False, "mode": "yolo",
                    "error": f"模型文件不存在: {model_path}",
                    "hint": "请调用 vision_verify_food(image_id) 进行视觉识别兜底",
                },
                ensure_ascii=False,
            )

        def _predict() -> list[dict]:
            global _yolo_model
            from ultralytics import YOLO

            if _yolo_model is None:
                _yolo_model = YOLO(str(model_path))
            results = _yolo_model.predict(source=str(image_path), conf=conf_threshold, verbose=False)
            detections = []
            result = results[0]
            if result.boxes is not None:
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    conf = round(float(box.conf[0]), 4)
                    detections.append(
                        {
                            "class_name": result.names.get(class_id, str(class_id)),
                            "class_name_cn": None,
                            "confidence": conf,
                            "bbox": [round(value, 2) for value in box.xyxy[0].tolist()],
                            "low_confidence": conf < 0.25,
                        }
                    )
            return detections

        detections = await asyncio.to_thread(_predict)
        low_conf_count = sum(1 for d in detections if d.get("low_confidence"))

        # ---- 自动保存检测记录到数据库 ----
        task_uuid_str = None
        import uuid as _uuid
        db = SessionLocal()
        try:
            scene = (
                db.query(DetectionScene)
                .filter(
                    DetectionScene.name == "food_detection",
                    DetectionScene.is_active == True,
                )
                .first()
            )
            if scene is None:
                raise RuntimeError("默认食物检测场景不存在或未启用")

            task_uuid_str = str(_uuid.uuid4())
            task = DetectionTask(
                user_id=None,  # Agent 工具当前没有用户上下文
                scene_id=scene.id,
                task_uuid=task_uuid_str,
                image_path=str(image_path),
                status="completed",
                detections=detections,
                total_objects=len(detections),
                inference_time=None,
                conf_threshold=conf_threshold,
                iou_threshold=0.45,
            )
            db.add(task)
            db.commit()
        except Exception as exc:
            db.rollback()
            task_uuid_str = None
            logger.warning("保存检测记录失败（数据库可能未就绪）: %s", exc)
        finally:
            db.close()

        return json.dumps(
            {
                "success": True,
                "mode": "yolo",
                "image_id": image_id,
                "task_uuid": task_uuid_str,
                "detections": detections,
                "total_objects": len(detections),
                "low_confidence_count": low_conf_count,
                "hint": (
                    f"有 {low_conf_count} 个低置信度结果(confidence<0.25)，"
                    "可调用 vision_verify_food(image_id) 进行视觉兜底验证"
                ) if low_conf_count > 0 else None,
            },
            ensure_ascii=False,
        )
    except Exception as exc:
        logger.exception("食物检测工具执行失败")
        return json.dumps({"success": False, "error": str(exc)}, ensure_ascii=False)


# ==================================================================
# 工具 1：视觉识别兜底（LLM Vision Fallback）
# ==================================================================

async def vision_verify_food(image_id: str) -> str:
    """当 YOLO 模型不存在、检测失败或结果低置信度时，用多模态 LLM
    直接观察图片进行食物识别兜底。

    对 image_id 对应的图片调用视觉语言模型（Qwen2.5-VL），
    返回识别到的食物列表和简要描述。适合处理 YOLO 不认识的食物类别。

    Args:
        image_id: 图片唯一标识（由系统上传时生成）

    Returns:
        JSON: {"success": bool, "foods": [{"name": "...", "confidence": "high/medium/low"}], ...}
    """
    try:
        image_path = image_store.get_path(image_id)
        if not image_path or not Path(image_path).exists():
            return json.dumps(
                {"success": False, "error": f"图片不存在: {image_id}"},
                ensure_ascii=False,
            )

        # 读取图片并转 base64
        with open(image_path, "rb") as f:
            img_data = base64.standard_b64encode(f.read()).decode("utf-8")

        # 判断图片类型
        suffix = Path(image_path).suffix.lower()
        mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}
        media_type = f"image/{mime.get(suffix.lstrip('.'), 'jpeg')}"

        # 调用视觉 LLM
        def _vision_call() -> dict:
            global _vision_llm
            from langchain_openai import ChatOpenAI

            if _vision_llm is None:
                _vision_llm = ChatOpenAI(
                    model=settings.VISION_MODEL,
                    openai_api_key=settings.OPENAI_API_KEY,
                    openai_api_base=settings.OPENAI_BASE_URL,
                    temperature=0.1,
                    max_tokens=1024,
                )

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{img_data}",
                                "detail": "auto",
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "你是一个食物识别助手。请仔细观察这张图片，识别图中所有的食物。\n\n"
                                "要求：\n"
                                "1. 列出你能识别的每一种食物（中英文名称）\n"
                                "2. 给出每种食物的置信度（high/medium/low）\n"
                                "3. 如果看不清或不确定，标注为 'uncertain'\n"
                                "4. 按 JSON 格式返回: {\"foods\": [{\"name\": \"...\", \"cn\": \"...\", \"confidence\": \"high/medium/low\"}]}\n\n"
                                "请直接返回 JSON，不要其他文字。"
                            ),
                        },
                    ],
                }
            ]

            response = _vision_llm.invoke(messages)
            return response.content

        result = await asyncio.to_thread(_vision_call)

        # 尝试解析 JSON
        try:
            parsed = json.loads(result)
            return json.dumps(
                {
                    "success": True,
                    "mode": "vision_fallback",
                    "image_id": image_id,
                    "foods": parsed.get("foods", []),
                },
                ensure_ascii=False,
            )
        except json.JSONDecodeError:
            # LLM 没按 JSON 格式返回，直接当文本
            return json.dumps(
                {
                    "success": True,
                    "mode": "vision_fallback",
                    "image_id": image_id,
                    "foods": [],
                    "raw_response": result,
                },
                ensure_ascii=False,
            )

    except Exception as exc:
        logger.exception("视觉识别兜底失败")
        return json.dumps(
            {"success": False, "error": str(exc)},
            ensure_ascii=False,
        )


# ==================================================================
# 工具 2：单食物营养查询
# ==================================================================

async def query_food_calories(food_name: str) -> str:
    """查询指定食物的营养数据（每 100g）。

    在 FoodNutrition 表中模糊匹配食物名称（支持中英文），
    返回热量、蛋白质、脂肪、碳水化合物和膳食纤维。

    Args:
        food_name: 食物名称（中文或英文）

    Returns:
        格式化的营养信息文本，如果未找到则返回提示信息。
    """
    def _query_sync(food_name: str) -> str:
        db = SessionLocal()
        try:
            # 模糊查询：先精确匹配，再模糊匹配
            food = (
                db.query(FoodNutrition)
                .filter(
                    (FoodNutrition.food_name == food_name.lower())
                    | (FoodNutrition.food_name_cn == food_name)
                )
                .first()
            )

            if food is None:
                # 模糊匹配
                food = (
                    db.query(FoodNutrition)
                    .filter(
                        FoodNutrition.food_name.ilike(f"%{food_name}%")
                        | FoodNutrition.food_name_cn.ilike(f"%{food_name}%")
                    )
                    .first()
                )

        except SQLAlchemyError as exc:
            logger.warning("营养数据库不可用，使用内置演示数据: %s", exc)
            food = None
        finally:
            db.close()

        if food is None:
            food = _builtin_food(food_name)
        if food is None:
            return (
                f"未在数据库中找到「{food_name}」的营养数据。"
                f"请尝试使用更通用的食物名称（如'米饭'而非'蛋炒饭'），"
                f"或手动输入该食物的营养信息。"
            )

        values = _food_values(food)
        return (
            f"【{values['cn']} ({values['name']})】\n"
            f"每 100g 营养成分：\n"
            f"  - 热量: {values['calories']:.1f} kcal\n"
            f"  - 蛋白质: {values['protein']:.1f} g\n"
            f"  - 脂肪: {values['fat']:.1f} g\n"
            f"  - 碳水化合物: {values['carbs']:.1f} g\n"
            f"  - 膳食纤维: {values['fiber']:.1f} g\n"
            f"食物分类: {values['category']}\n"
            f"数据来源: {values['source']}"
        )

    return await asyncio.to_thread(_query_sync, food_name)


# ==================================================================
# 工具 3：按类别查询食物
# ==================================================================

async def query_food_by_category(category: str) -> str:
    """查询指定类别下的所有食物及其营养数据。

    Args:
        category: 食物分类名称（如 "fruit", "meat", "vegetable", "staple"）

    Returns:
        格式化的食物列表文本
    """
    def _query_sync(category: str) -> str:
        db = SessionLocal()
        try:
            foods = (
                db.query(FoodNutrition)
                .filter(FoodNutrition.category == category.lower())
                .order_by(FoodNutrition.calories_per_100g)
                .all()
            )

            if not foods:
                # 模糊匹配
                foods = (
                    db.query(FoodNutrition)
                    .filter(FoodNutrition.category.ilike(f"%{category}%"))
                    .order_by(FoodNutrition.calories_per_100g)
                    .all()
                )

            if not foods:
                return f"未找到分类为「{category}」的食物。支持的分类包括: fruit, meat, vegetable, staple, dairy, snack, beverage"

            lines = [f"「{category}」分类下的食物（共 {len(foods)} 项）："]
            for food in foods:
                lines.append(
                    f"  - {food.food_name_cn} ({food.food_name}): "
                    f"{food.calories_per_100g:.0f} kcal/100g, "
                    f"蛋白质 {food.protein_per_100g:.1f}g"
                )
            return "\n".join(lines)
        finally:
            db.close()

    return await asyncio.to_thread(_query_sync, category)


# ==================================================================
# 工具 4：计算总营养
# ==================================================================

async def calculate_total_nutrition(food_items_json: str) -> str:
    """根据食物清单和估算重量，计算总营养摄入。

    Args:
        food_items_json: JSON 字符串，格式为：
            [{"food_name": "apple", "estimated_weight_g": 200}, ...]

    Returns:
        格式化的总营养分析文本
    """
    def _calc_sync(food_items_json: str) -> str:
        try:
            items = json.loads(food_items_json)
        except json.JSONDecodeError:
            return "输入格式错误，请提供有效的 JSON 数组，如：[{\"food_name\": \"apple\", \"estimated_weight_g\": 200}]"

        if not items:
            return "食物清单为空，无法计算。"

        db = SessionLocal()
        database_available = True
        try:
            total_calories = 0.0
            total_protein = 0.0
            total_fat = 0.0
            total_carbs = 0.0
            total_fiber = 0.0
            found_count = 0
            not_found = []

            lines = ["## 本餐营养分析结果\n"]

            for item in items:
                food_name = item.get("food_name", "")
                weight_g = float(item.get("estimated_weight_g", 100))

                food = None
                if database_available:
                    try:
                        food = (
                            db.query(FoodNutrition)
                            .filter(
                                (FoodNutrition.food_name == food_name.lower())
                                | (FoodNutrition.food_name_cn == food_name)
                            )
                            .first()
                        )
                    except SQLAlchemyError as exc:
                        logger.warning("营养数据库不可用，使用内置演示数据: %s", exc)
                        db.rollback()
                        database_available = False
                if food is None:
                    food = _builtin_food(food_name)

                if food:
                    values = _food_values(food)
                    factor = weight_g / 100.0
                    cal = values["calories"] * factor
                    prot = values["protein"] * factor
                    fat = values["fat"] * factor
                    carb = values["carbs"] * factor
                    fib = values["fiber"] * factor

                    total_calories += cal
                    total_protein += prot
                    total_fat += fat
                    total_carbs += carb
                    total_fiber += fib
                    found_count += 1

                    lines.append(
                        f"- {values['cn']} ({weight_g}g): "
                        f"{cal:.0f} kcal | "
                        f"蛋白质 {prot:.1f}g | "
                        f"脂肪 {fat:.1f}g | "
                        f"碳水 {carb:.1f}g"
                    )
                else:
                    not_found.append(food_name)

            lines.append("")
            lines.append("---")
            lines.append(f"## 汇总（已匹配 {found_count}/{len(items)} 项）")
            lines.append(f"- 🔥 总热量: {total_calories:.0f} kcal")
            lines.append(f"- 💪 总蛋白质: {total_protein:.1f} g")
            lines.append(f"- 🧈 总脂肪: {total_fat:.1f} g")
            lines.append(f"- 🍚 总碳水化合物: {total_carbs:.1f} g")
            lines.append(f"- 🌾 总膳食纤维: {total_fiber:.1f} g")

            # 宏量营养素比例
            total_macro = total_protein * 4 + total_fat * 9 + total_carbs * 4
            if total_macro > 0:
                lines.append("")
                lines.append("## 宏量营养素供能比")
                lines.append(
                    f"- 蛋白质: {total_protein * 4 / total_macro * 100:.0f}%")
                lines.append(f"- 脂肪: {total_fat * 9 / total_macro * 100:.0f}%")
                lines.append(
                    f"- 碳水化合物: {total_carbs * 4 / total_macro * 100:.0f}%")

            if not_found:
                lines.append("")
                lines.append(f"⚠️ 以下食物未在数据库中找到: {', '.join(not_found)}")

            return "\n".join(lines)
        finally:
            db.close()

    return await asyncio.to_thread(_calc_sync, food_items_json)


# ==================================================================
# 工具 5：获取用户档案
# ==================================================================

async def get_user_profile(user_id: int) -> str:
    """获取用户的健康档案信息。

    Args:
        user_id: 用户 ID

    Returns:
        格式化的用户档案文本
    """
    def _get_sync(user_id: int) -> str:
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return f"未找到用户 ID={user_id} 的信息。"

            return (
                f"用户信息：\n"
                f"  用户名: {user.username}\n"
                f"  状态: {'活跃' if user.is_active else '禁用'}\n"
                f"  注册时间: {user.created_at.strftime('%Y-%m-%d') if user.created_at else '未知'}\n"
                f"  最后登录: {user.last_login_at.strftime('%Y-%m-%d %H:%M') if user.last_login_at else '未知'}"
            )
        finally:
            db.close()

    return await asyncio.to_thread(_get_sync, user_id)


# ==================================================================
# 工具 6：保存检测记录
# ==================================================================

async def save_detection_record(
    user_id: int,
    scene_id: int,
    detections_json: str,
) -> str:
    """将检测结果持久化保存到数据库。

    Args:
        user_id: 用户 ID
        scene_id: 检测场景 ID
        detections_json: 检测结果 JSON 字符串

    Returns:
        保存确认信息
    """
    def _save_sync(user_id: int, scene_id: int, detections_json: str) -> str:
        try:
            detections_data = json.loads(detections_json)
        except json.JSONDecodeError:
            return "保存失败：检测结果格式无效"

        import uuid

        db = SessionLocal()
        try:
            task = DetectionTask(
                user_id=user_id,
                scene_id=scene_id,
                task_uuid=str(uuid.uuid4()),
                status="completed",
                detections=detections_data if isinstance(
                    detections_data, list) else [detections_data],
                total_objects=len(detections_data) if isinstance(
                    detections_data, list) else 1,
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            return f"✅ 检测记录已保存。任务 ID: {task.id}, UUID: {task.task_uuid}"
        finally:
            db.close()

    return await asyncio.to_thread(_save_sync, user_id, scene_id, detections_json)
