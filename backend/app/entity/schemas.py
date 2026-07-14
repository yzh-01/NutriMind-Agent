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
    model_name: str = Field(default="yolo26n", description="基础模型名称")
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
