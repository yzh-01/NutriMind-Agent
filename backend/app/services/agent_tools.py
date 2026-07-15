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
import json
import logging
from app.database.session import get_session_local
from app.entity.db_models import DetectionTask, FoodNutrition, User

logger = logging.getLogger(__name__)


# ==================================================================
# 工具 1：单食物营养查询
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
        db = get_session_local()()
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

            if food is None:
                return (
                    f"未在数据库中找到「{food_name}」的营养数据。"
                    f"请尝试使用更通用的食物名称（如'米饭'而非'蛋炒饭'），"
                    f"或手动输入该食物的营养信息。"
                )

            return (
                f"【{food.food_name_cn} ({food.food_name})】\n"
                f"每 100{food.serving_unit} 营养成分：\n"
                f"  - 热量: {food.calories_per_100g:.1f} kcal\n"
                f"  - 蛋白质: {food.protein_per_100g:.1f} g\n"
                f"  - 脂肪: {food.fat_per_100g:.1f} g\n"
                f"  - 碳水化合物: {food.carbs_per_100g:.1f} g\n"
                f"  - 膳食纤维: {food.fiber_per_100g:.1f} g\n"
                f"食物分类: {food.category or '未分类'}\n"
                f"数据来源: {food.source or '系统内置'}"
            )
        finally:
            db.close()

    return await asyncio.to_thread(_query_sync, food_name)


# ==================================================================
# 工具 2：按类别查询食物
# ==================================================================

async def query_food_by_category(category: str) -> str:
    """查询指定类别下的所有食物及其营养数据。

    Args:
        category: 食物分类名称（如 "fruit", "meat", "vegetable", "staple"）

    Returns:
        格式化的食物列表文本
    """
    def _query_sync(category: str) -> str:
        db = get_session_local()()
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
# 工具 3：计算总营养
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

        db = get_session_local()()
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

                food = (
                    db.query(FoodNutrition)
                    .filter(
                        (FoodNutrition.food_name == food_name.lower())
                        | (FoodNutrition.food_name_cn == food_name)
                    )
                    .first()
                )

                if food:
                    factor = weight_g / 100.0
                    cal = food.calories_per_100g * factor
                    prot = food.protein_per_100g * factor
                    fat = food.fat_per_100g * factor
                    carb = food.carbs_per_100g * factor
                    fib = food.fiber_per_100g * factor

                    total_calories += cal
                    total_protein += prot
                    total_fat += fat
                    total_carbs += carb
                    total_fiber += fib
                    found_count += 1

                    lines.append(
                        f"- {food.food_name_cn} ({weight_g}g): "
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
# 工具 4：获取用户档案
# ==================================================================

async def get_user_profile(user_id: int) -> str:
    """获取用户的健康档案信息。

    Args:
        user_id: 用户 ID

    Returns:
        格式化的用户档案文本
    """
    def _get_sync(user_id: int) -> str:
        db = get_session_local()()
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
# 工具 5：保存检测记录
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

        db = get_session_local()()
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
