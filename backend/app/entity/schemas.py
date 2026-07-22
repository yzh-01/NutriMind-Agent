from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional, List, Any, Dict
from datetime import datetime


class ApiResponse(BaseModel):
    """通用 API 响应"""
    code: int = Field(default=200, description="状态码")
    message: str = Field(default="success", description="响应消息")
    data: Optional[Any] = Field(default=None, description="响应数据")


class UserRegister(BaseModel):
    """用户注册请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, description="密码")


class UserLogin(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class ChangePassword(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=6, description="新密码")


class UserUpdate(BaseModel):
    """用户更新请求"""
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None


class UserResponse(BaseModel):
    """用户响应"""
    id: int
    username: str
    email: str
    phone: Optional[str] = None
    avatar: Optional[str] = None
    is_active: bool
    is_superuser: bool
    roles: List[str] = []
    last_login_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ============================================================
# 目标检测相关 Schema（AI/算法工程师负责）
# ============================================================

class DetectionRequest(BaseModel):
    """单图检测请求"""
    scene_id: int = Field(..., description="检测场景 ID")
    conf_threshold: float = Field(
        default=0.25, ge=0.0, le=1.0, description="置信度阈值")
    iou_threshold: float = Field(
        default=0.45, ge=0.0, le=1.0, description="IoU 阈值")


class BoundingBox(BaseModel):
    """检测框"""
    class_name: str = Field(..., description="类别英文名")
    class_name_cn: Optional[str] = Field(default=None, description="类别中文名")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    bbox: List[float] = Field(..., description="边界框坐标 [x1, y1, x2, y2]")
    low_confidence: bool = Field(default=False, description="低置信度标记（<0.25），供 Agent 判断")


class ChatRequest(BaseModel):
    """发送给营养智能体的消息。"""

    message: str = Field(default="", max_length=4000,
                         description="用户消息；有检测结果时可为空")
    session_id: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="会话 ID；不传时由服务端生成",
    )
    detections: List[BoundingBox] = Field(
        default_factory=list,
        max_length=100,
        description="YOLO 返回的食物检测结果",
    )


class AgentToolCall(BaseModel):
    """智能体执行过的工具调用。"""

    name: str
    args: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """营养智能体响应。"""

    session_id: str
    response: str
    tool_calls: List[AgentToolCall] = Field(default_factory=list)
    analysis_result: Optional[str] = None


class ChatSessionCreate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)


class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    image_id: Optional[str] = None
    image_url: Optional[str] = None
    tool_calls: List[AgentToolCall] = Field(default_factory=list)
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSessionResponse(BaseModel):
    session_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageResponse] = Field(default_factory=list)


class ImageChatResponse(ChatResponse):
    """图片营养分析响应。"""

    image_id: str
    detection_mode: str
    detections: List[BoundingBox] = Field(default_factory=list)


class DetectionResponse(BaseModel):
    """单图检测响应"""
    task_id: int = Field(..., description="任务数据库 ID")
    task_uuid: str = Field(..., description="任务 UUID")
    detections: List[BoundingBox] = Field(
        default_factory=list, description="检测结果列表")
    total_objects: int = Field(default=0, description="检测到的目标总数")
    inference_time: float = Field(..., description="推理耗时（秒）")
    image_url: Optional[str] = Field(
        default=None, description="上传图片的 MinIO URL")
    created_at: Optional[datetime] = Field(default=None, description="任务创建时间")

    model_config = ConfigDict(from_attributes=True)


class DetectionTaskSummary(BaseModel):
    """检测任务摘要（列表用）"""
    id: int
    task_uuid: str
    scene_id: int
    status: str
    total_objects: int
    inference_time: Optional[float] = None
    image_url: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DetectionTaskListResponse(BaseModel):
    """检测任务分页列表"""
    items: List[DetectionTaskSummary]
    total: int
    page: int
    page_size: int


class SceneResponse(BaseModel):
    """检测场景响应"""
    id: int
    name: str
    display_name: str
    category: str
    class_names: List[str]
    class_names_cn: Optional[List[str]] = None
    model_path: Optional[str] = None
    is_active: bool
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================
# 模型训练相关 Schema（AI/算法工程师负责）
# ============================================================

class TrainingTaskCreate(BaseModel):
    """创建训练任务请求"""
    scene_id: Optional[int] = Field(default=None, description="关联检测场景 ID")
    model_name: str = Field(default="yolo11s", description="基础模型名称")
    data_yaml: str = Field(..., description="数据集 data.yaml 文件路径")
    epochs: int = Field(default=100, gt=0, le=1000, description="训练轮数")
    img_size: int = Field(default=640, ge=320, le=1920, description="输入图像尺寸")
    batch_size: int = Field(default=16, gt=0, le=256, description="批次大小")


class TrainingTaskResponse(BaseModel):
    """训练任务响应"""
    id: int
    task_uuid: str
    model_name: str
    status: str
    metrics: Optional[Dict[str, Any]] = Field(
        default=None, description="训练指标（mAP、Precision、Recall、Loss 等）")
    progress: float = Field(default=0.0, description="训练进度百分比")
    data_yaml: Optional[str] = None
    epochs: int
    img_size: int
    batch_size: int
    output_model_path: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TrainingTaskListResponse(BaseModel):
    """训练任务分页列表"""
    items: List[TrainingTaskResponse]
    total: int
    page: int
    page_size: int


class ModelInfoResponse(BaseModel):
    """模型文件信息"""
    name: str = Field(..., description="模型文件名")
    path: str = Field(..., description="模型文件路径")
    size_bytes: int = Field(..., description="文件大小（字节）")
    created_at: datetime = Field(..., description="文件创建时间")

    model_config = ConfigDict(from_attributes=True)


class TrainingMetricsLineChart(BaseModel):
    """训练折线图数据 — 每个 epoch 的指标，前端直接用于 Chart.js/ECharts"""
    task_uuid: str = Field(..., description="训练任务 UUID")
    model_name: str = Field(..., description="模型名称")
    epochs: List[dict] = Field(
        default_factory=list,
        description="per-epoch 数据，每项含 epoch/train_box_loss/train_cls_loss/val_box_loss/val_cls_loss/mAP50/mAP50_95/precision/recall"
    )
    final_metrics: Optional[dict] = Field(default=None, description="最终汇总指标")


class DetectionUploadResponse(BaseModel):
    """图片上传检测响应（兼容现有 DetectionResponse）"""
    task_id: Optional[int] = Field(default=None, description="任务数据库 ID")
    task_uuid: str = Field(..., description="任务 UUID")
    detections: list = Field(default_factory=list, description="检测结果列表")
    total_objects: int = Field(default=0, description="检测到的目标总数")
    inference_time: float = Field(..., description="推理耗时（秒）")


# ============================================================
# 食物营养相关 Schema（Agent 工具用）
# ============================================================

class FoodNutritionResponse(BaseModel):
    """食物营养信息响应"""
    id: int
    food_name: str
    food_name_cn: str
    calories_per_100g: float
    protein_per_100g: float
    fat_per_100g: float
    carbs_per_100g: float
    fiber_per_100g: float
    serving_size: float
    serving_unit: str
    category: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class NutritionQuery(BaseModel):
    """食物营养查询"""
    food_name: str = Field(..., min_length=1,
                           max_length=100, description="食物名称")


class CalorieCalculationRequest(BaseModel):
    """卡路里计算请求"""
    food_items: List[Dict[str, Any]] = Field(
        ..., description="食物项列表 [{\"food_name\": \"apple\", \"estimated_weight_g\": 200}]"
    )


# ============================================================
# 通用 Schema
# ============================================================

class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页大小")


# ============================================================
# 用户管理相关 Schema（Dashboard 管理端）
# ============================================================

class UserListItem(BaseModel):
    """用户列表项"""
    id: int
    username: str
    email: str
    phone: Optional[str] = None
    avatar: Optional[str] = None
    is_active: bool
    is_superuser: bool
    roles: List[str] = []
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """用户列表分页响应"""
    items: List[UserListItem]
    total: int
    page: int
    page_size: int


class UserDetailResponse(BaseModel):
    """用户详情响应"""
    id: int
    username: str
    email: str
    phone: Optional[str] = None
    avatar: Optional[str] = None
    is_active: bool
    is_superuser: bool
    roles: List[str] = []
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    # 扩展统计
    total_detection_tasks: int = 0
    total_training_tasks: int = 0

    model_config = ConfigDict(from_attributes=True)


class ToggleUserStatusRequest(BaseModel):
    """启用/禁用用户请求"""
    is_active: bool = Field(..., description="是否启用")


class UpdateUserRoleRequest(BaseModel):
    """修改用户角色请求"""
    role_names: List[str] = Field(..., description="角色名称列表")


class UpdateUserSuperuserRequest(BaseModel):
    """修改用户管理员状态请求"""
    is_superuser: bool = Field(..., description="是否超级管理员")


# ============================================================
# Dashboard 看板相关 Schema
# ============================================================

class DashboardOverview(BaseModel):
    """看板总览数据"""
    total_users: int = Field(default=0, description="用户总数")
    active_users: int = Field(default=0, description="活跃用户数")
    total_detection_scenes: int = Field(default=0, description="检测场景总数")
    total_detection_tasks: int = Field(default=0, description="检测任务总数")
    total_training_tasks: int = Field(default=0, description="训练任务总数")
    total_food_items: int = Field(default=0, description="食物营养数据条数")


class TaskStatusCount(BaseModel):
    """任务状态统计"""
    status: str = Field(..., description="状态")
    count: int = Field(default=0, description="数量")


class DetectionStats(BaseModel):
    """检测任务统计"""
    total: int = Field(default=0, description="检测任务总数")
    completed: int = Field(default=0, description="已完成数")
    failed: int = Field(default=0, description="失败数")
    pending: int = Field(default=0, description="等待中数")
    processing: int = Field(default=0, description="处理中数")
    total_objects_detected: int = Field(default=0, description="累计检测目标数")
    avg_inference_time: Optional[float] = Field(
        default=None, description="平均推理耗时（秒）")


class TrainingStats(BaseModel):
    """训练任务统计"""
    total: int = Field(default=0, description="训练任务总数")
    completed: int = Field(default=0, description="已完成数")
    failed: int = Field(default=0, description="失败数")
    running: int = Field(default=0, description="运行中数")
    pending: int = Field(default=0, description="等待中数")
    paused: int = Field(default=0, description="已暂停数")


class UserStats(BaseModel):
    """用户统计"""
    total: int = Field(default=0, description="用户总数")
    active: int = Field(default=0, description="启用用户数")
    superusers: int = Field(default=0, description="管理员数")
    new_today: int = Field(default=0, description="今日新增")


class DashboardStats(BaseModel):
    """看板完整统计数据"""
    overview: DashboardOverview
    detection: DetectionStats
    training: TrainingStats
    users: UserStats
