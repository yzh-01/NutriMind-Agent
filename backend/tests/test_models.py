"""
数据库模型测试：CRUD 操作、关系、约束
"""
import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.entity.db_models import (
    User, Role, Permission, UserRole, RolePermission,
    DetectionScene, DetectionTask,
    TrainingTask, FoodNutrition,
)


class TestUserModel:
    """User 模型测试"""

    def test_create_user(self, db):
        """创建用户基本字段"""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_xxx",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.is_superuser is False
        assert user.created_at is not None

    def test_username_unique_constraint(self, db):
        """用户名唯一约束"""
        db.add(User(username="unique1", email="a@example.com", hashed_password="hash"))
        db.commit()
        db.add(User(username="unique1", email="b@example.com", hashed_password="hash"))
        with pytest.raises(IntegrityError):
            db.commit()

    def test_email_unique_constraint(self, db):
        """邮箱唯一约束"""
        db.add(User(username="user_a", email="same@example.com",
               hashed_password="hash"))
        db.commit()
        db.add(User(username="user_b", email="same@example.com",
               hashed_password="hash"))
        with pytest.raises(IntegrityError):
            db.commit()

    def test_superuser_flag(self, db):
        """超级管理员标记"""
        user = User(
            username="admin",
            email="admin@example.com",
            hashed_password="hash",
            is_superuser=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        assert user.is_superuser is True

    def test_inactive_user(self, db):
        """禁用用户标记"""
        user = User(
            username="disabled",
            email="disabled@example.com",
            hashed_password="hash",
            is_active=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        assert user.is_active is False


class TestRoleModel:
    """Role / Permission 模型测试"""

    def test_create_role(self, db):
        """创建角色"""
        role = Role(name="admin", display_name="管理员", description="系统管理员")
        db.add(role)
        db.commit()
        db.refresh(role)
        assert role.id is not None
        assert role.name == "admin"
        assert role.is_system is False

    def test_role_unique_name(self, db):
        """角色名唯一约束"""
        db.add(Role(name="editor", display_name="编辑"))
        db.commit()
        db.add(Role(name="editor", display_name="编辑2"))
        with pytest.raises(IntegrityError):
            db.commit()

    def test_create_permission(self, db):
        """创建权限"""
        perm = Permission(code="detection:read",
                          name="查看检测", module="detection")
        db.add(perm)
        db.commit()
        db.refresh(perm)
        assert perm.id is not None
        assert perm.code == "detection:read"

    def test_user_role_association(self, db):
        """用户-角色关联"""
        user = User(username="roleuser", email="role@example.com",
                    hashed_password="hash")
        role = Role(name="viewer", display_name="观察者")
        db.add_all([user, role])
        db.commit()
        db.refresh(user)
        db.refresh(role)

        user_role = UserRole(user_id=user.id, role_id=role.id)
        db.add(user_role)
        db.commit()
        db.refresh(user_role)

        assert user_role.id is not None
        assert user_role.user_id == user.id
        assert user_role.role_id == role.id


class TestDetectionModels:
    """检测场景 & 任务模型测试"""

    def test_create_detection_scene(self, db):
        """创建检测场景"""
        scene = DetectionScene(
            name="food_detection",
            display_name="食物检测",
            category="food",
            class_names=["apple", "banana"],
            class_names_cn=["苹果", "香蕉"],
        )
        db.add(scene)
        db.commit()
        db.refresh(scene)

        assert scene.id is not None
        assert scene.name == "food_detection"
        assert scene.is_active is True
        assert scene.conf_threshold == 0.25

    def test_create_detection_task(self, db):
        """创建检测任务"""
        scene = DetectionScene(
            name="test_scene",
            display_name="测试场景",
            category="test",
            class_names=["obj"],
        )
        db.add(scene)
        db.commit()
        db.refresh(scene)

        task = DetectionTask(
            scene_id=scene.id,
            image_path="/tmp/test.jpg",
            status="pending",
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        assert task.id is not None
        assert task.task_uuid is not None
        assert task.status == "pending"
        assert task.total_objects == 0

    def test_scene_task_relationship(self, db):
        """场景-任务关联关系"""
        scene = DetectionScene(
            name="rel_scene",
            display_name="关联测试",
            category="test",
            class_names=["obj"],
        )
        db.add(scene)
        db.commit()
        db.refresh(scene)

        task = DetectionTask(scene_id=scene.id, status="pending")
        db.add(task)
        db.commit()
        db.refresh(scene)

        assert len(scene.detection_tasks) == 1
        assert scene.detection_tasks[0].scene_id == scene.id


class TestTrainingModels:
    """训练任务模型测试"""

    def test_create_training_task(self, db):
        """创建训练任务"""
        task = TrainingTask(
            model_name="yolo26n",
            data_yaml="/data/food.yaml",
            epochs=50,
            batch_size=8,
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        assert task.id is not None
        assert task.task_uuid is not None
        assert task.status == "pending"
        assert task.epochs == 50
        assert task.progress == 0.0

    def test_training_task_defaults(self, db):
        """训练任务默认值"""
        task = TrainingTask(
            model_name="yolo26n",
            data_yaml="/data/test.yaml",
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        assert task.epochs == 100
        assert task.img_size == 640
        assert task.batch_size == 16


class TestFoodNutrition:
    """食物营养模型测试"""

    def test_create_food_nutrition(self, db):
        """创建食物营养记录"""
        food = FoodNutrition(
            food_name="apple",
            food_name_cn="苹果",
            calories_per_100g=52.0,
            protein_per_100g=0.3,
            fat_per_100g=0.2,
            carbs_per_100g=14.0,
            fiber_per_100g=2.4,
            category="fruit",
        )
        db.add(food)
        db.commit()
        db.refresh(food)

        assert food.id is not None
        assert food.food_name == "apple"
        assert food.calories_per_100g == 52.0
        assert food.serving_size == 100.0

    def test_food_nutrition_repr(self, db):
        """食物营养 __repr__"""
        food = FoodNutrition(
            food_name="banana",
            food_name_cn="香蕉",
            calories_per_100g=89.0,
        )
        assert "香蕉" in repr(food)
        assert "89.0" in repr(food)


class TestCascadeDelete:
    """级联删除测试"""

    def test_user_cascade_delete_roles(self, db):
        """删除用户时级联删除用户角色关联"""
        user = User(username="cascade_user",
                    email="cascade@example.com", hashed_password="hash")
        role = Role(name="cascade_role", display_name="级联角色")
        db.add_all([user, role])
        db.commit()
        db.refresh(user)
        db.refresh(role)

        user_role = UserRole(user_id=user.id, role_id=role.id)
        db.add(user_role)
        db.commit()

        # 删除用户
        db.delete(user)
        db.commit()

        # UserRole 应该被级联删除
        remaining = db.query(UserRole).filter(
            UserRole.user_id == user.id).all()
        assert len(remaining) == 0

    def test_scene_cascade_delete_tasks(self, db):
        """删除场景时级联删除关联任务"""
        scene = DetectionScene(
            name="del_scene",
            display_name="删除测试",
            category="test",
            class_names=["obj"],
        )
        db.add(scene)
        db.commit()
        db.refresh(scene)

        task = DetectionTask(scene_id=scene.id, status="pending")
        db.add(task)
        db.commit()

        db.delete(scene)
        db.commit()

        remaining = db.query(DetectionTask).filter(
            DetectionTask.scene_id == scene.id).all()
        assert len(remaining) == 0
