import uuid
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, JSON, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.session import Base


class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    email = Column(String(100), unique=True, nullable=False, index=True, comment="邮箱")
    hashed_password = Column(String(255), nullable=False, comment="加密密码")
    phone = Column(String(20), nullable=True, comment="手机号")
    avatar = Column(String(500), nullable=True, comment="头像 URL")
    is_active = Column(Boolean, default=True, comment="是否启用")
    is_superuser = Column(Boolean, default=False, comment="是否超级管理员")
    last_login_at = Column(DateTime, nullable=True, comment="最后登录时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")
    
    # 关联
    user_roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")


class ChatSession(Base):
    """可恢复的智能体会话。session_uuid 是暴露给前端的稳定标识。"""
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_uuid = Column(String(100), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False, default="新对话")
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(Base):
    """会话消息，用于跨进程/重启恢复历史。"""
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    # 图片文件仍由 ImageStore 管理；数据库保存安全引用，用于恢复历史消息。
    image_id = Column(String(64), nullable=True, index=True)
    tool_calls = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    session = relationship("ChatSession", back_populates="messages")


class Role(Base):
    """角色表"""
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False, comment="角色标识")
    display_name = Column(String(100), nullable=False, comment="显示名称")
    description = Column(String(500), nullable=True, comment="角色描述")
    is_system = Column(Boolean, default=False, comment="是否系统角色")
    
    # 关联
    user_roles = relationship("UserRole", back_populates="role")
    role_permissions = relationship("RolePermission", back_populates="role")


class Permission(Base):
    """权限表"""
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True)
    code = Column(String(100), unique=True, nullable=False, comment="权限编码")
    name = Column(String(100), nullable=False, comment="权限名称")
    module = Column(String(50), nullable=False, comment="所属模块")


class UserRole(Base):
    """用户-角色关联表"""
    __tablename__ = "user_roles"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    
    # 关联
    user = relationship("User", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")


class RolePermission(Base):
    """角色-权限关联表"""
    __tablename__ = "role_permissions"
    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id"), nullable=False)

    # 关联
    role = relationship("Role", back_populates="role_permissions")


# ============================================================
# 目标检测 & 模型训练相关模型（AI/算法工程师负责）
# ============================================================

class DetectionScene(Base):
    """检测场景表 — 定义可用的检测场景（如 food_detection）"""
    __tablename__ = "detection_scenes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True, comment="场景唯一标识")
    display_name = Column(String(200), nullable=False, comment="场景显示名称")
    category = Column(String(50), nullable=False, default="food", comment="场景分类")
    class_names = Column(JSON, nullable=False, comment="英文类别名列表")
    class_names_cn = Column(JSON, nullable=True, comment="中文类别名列表")
    model_path = Column(String(500), nullable=True, comment="该场景默认模型文件路径")
    conf_threshold = Column(Float, default=0.25, comment="默认置信度阈值")
    iou_threshold = Column(Float, default=0.45, comment="默认 IoU 阈值")
    is_active = Column(Boolean, default=True, comment="是否启用")
    description = Column(String(500), nullable=True, comment="场景描述")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # 关联
    detection_tasks = relationship("DetectionTask", back_populates="scene")

    def __repr__(self):
        return f"<DetectionScene(name={self.name}, category={self.category})>"


class DetectionTask(Base):
    """检测任务表 — 记录每次图片检测的请求与结果"""
    __tablename__ = "detection_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="提交用户 ID")
    scene_id = Column(Integer, ForeignKey("detection_scenes.id"), nullable=False, comment="检测场景 ID")
    task_uuid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), comment="任务唯一标识")
    image_url = Column(String(1000), nullable=True, comment="上传图片的 MinIO URL")
    image_path = Column(String(500), nullable=True, comment="图片本地路径（临时）")
    status = Column(
        Enum("pending", "processing", "completed", "failed", name="detection_status"),
        default="pending",
        comment="任务状态"
    )
    detections = Column(JSON, nullable=True, comment="检测结果 JSON（BoundingBox 列表）")
    total_objects = Column(Integer, default=0, comment="检测到的目标总数")
    inference_time = Column(Float, nullable=True, comment="推理耗时（秒）")
    conf_threshold = Column(Float, default=0.25, comment="实际使用的置信度阈值")
    iou_threshold = Column(Float, default=0.45, comment="实际使用的 IoU 阈值")
    error_message = Column(Text, nullable=True, comment="错误信息")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    # 关联
    scene = relationship("DetectionScene", back_populates="detection_tasks")

    def __repr__(self):
        return f"<DetectionTask(uuid={self.task_uuid}, status={self.status}, objects={self.total_objects})>"


class TrainingTask(Base):
    """训练任务表 — 记录模型训练的配置、状态和结果"""
    __tablename__ = "training_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="提交用户 ID")
    scene_id = Column(Integer, ForeignKey("detection_scenes.id"), nullable=True, comment="关联场景 ID")
    task_uuid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), comment="任务唯一标识")
    model_name = Column(String(100), nullable=False, default="yolo11s", comment="基础模型名称")
    data_yaml = Column(String(500), nullable=False, comment="数据集 data.yaml 路径")
    epochs = Column(Integer, nullable=False, default=100, comment="训练轮数")
    img_size = Column(Integer, default=640, comment="输入图像尺寸")
    batch_size = Column(Integer, default=16, comment="批次大小")
    status = Column(
        Enum("pending", "running", "completed", "failed", "paused", name="training_status"),
        default="pending",
        comment="训练状态"
    )
    metrics = Column(JSON, nullable=True, comment="训练指标 JSON（mAP、Precision、Recall、Loss）")
    progress = Column(Float, default=0.0, comment="训练进度 0-100")
    output_model_path = Column(String(500), nullable=True, comment="输出模型文件路径")
    error_message = Column(Text, nullable=True, comment="错误信息")
    started_at = Column(DateTime, nullable=True, comment="开始训练时间")
    completed_at = Column(DateTime, nullable=True, comment="完成训练时间")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    def __repr__(self):
        return f"<TrainingTask(uuid={self.task_uuid}, model={self.model_name}, status={self.status})>"


class FoodNutrition(Base):
    """食物营养信息表 — 存储常用食物的营养数据，供 Agent 工具查询"""
    __tablename__ = "food_nutrition"

    id = Column(Integer, primary_key=True, autoincrement=True)
    food_name = Column(String(100), nullable=False, index=True, comment="食物英文名")
    food_name_cn = Column(String(100), nullable=False, index=True, comment="食物中文名")
    calories_per_100g = Column(Float, nullable=False, comment="每100g 热量（kcal）")
    protein_per_100g = Column(Float, default=0.0, comment="每100g 蛋白质（g）")
    fat_per_100g = Column(Float, default=0.0, comment="每100g 脂肪（g）")
    carbs_per_100g = Column(Float, default=0.0, comment="每100g 碳水化合物（g）")
    fiber_per_100g = Column(Float, default=0.0, comment="每100g 膳食纤维（g）")
    serving_size = Column(Float, default=100.0, comment="标准份量（g）")
    serving_unit = Column(String(20), default="g", comment="份量单位")
    category = Column(String(50), nullable=True, index=True, comment="食物分类（如 fruit/meat/vegetable）")
    source = Column(String(200), nullable=True, comment="数据来源")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")

    def __repr__(self):
        return f"<FoodNutrition(name={self.food_name_cn}, calories={self.calories_per_100g}kcal/100g)>"


# ============================================================
# 用户身体资料与目标
# ============================================================

class BodyProfile(Base):
    """用户身体资料表"""
    __tablename__ = "body_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True,
                     nullable=False, comment="用户 ID")
    current_weight_kg = Column(Float, nullable=True, comment="当前体重 kg")
    height_cm = Column(Float, nullable=True, comment="身高 cm")
    birth_date = Column(DateTime, nullable=True, comment="出生日期")
    sex_for_calculation = Column(
        String(20), nullable=True,
        comment="性别用于公式计算: male/female/unspecified"
    )
    activity_level = Column(
        String(20), nullable=True,
        comment="活动水平: sedentary/light/moderate/high/very_high"
    )
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now,
                        onupdate=datetime.now, comment="更新时间")

    def __repr__(self):
        return f"<BodyProfile(user_id={self.user_id}, weight={self.current_weight_kg}kg)>"


class GoalProfile(Base):
    """用户目标表"""
    __tablename__ = "goal_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True,
                     nullable=False, comment="用户 ID")
    mode = Column(
        String(20), nullable=True,
        comment="目标模式: cut/muscle/maintain"
    )
    target_weight_kg = Column(Float, nullable=True, comment="目标体重 kg")
    daily_calories_kcal = Column(Integer, nullable=True, comment="每日热量目标 kcal")
    protein_target_g = Column(Integer, nullable=True, comment="每日蛋白质目标 g")
    training_days_per_week = Column(Integer, nullable=True, comment="每周训练天数 1-7")
    started_at = Column(DateTime, nullable=True, comment="目标开始日期")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now,
                        onupdate=datetime.now, comment="更新时间")

    def __repr__(self):
        return f"<GoalProfile(user_id={self.user_id}, mode={self.mode})>"
