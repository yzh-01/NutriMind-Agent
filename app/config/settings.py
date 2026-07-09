"""全局配置模块。"""

from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """全局配置类。"""

    # 应用基础配置
    APP_NAME: str = "XJTU-VisAgent"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # 数据库配置
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "xjtu-visagent"
    DB_USER: str = "root"
    DB_PASSWORD: str = "root"

    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    # MinIO 配置
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "visagent-images"
    MINIO_SECURE: bool = False

    # JWT 配置
    JWT_SECRET_KEY: str = "liu13568610305"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 大模型配置
    OPENAI_API_KEY: str = "sk-ejhpvwtrgzcpkpudikolfzwntfvblkgtqabuhdfznovgudkb"
    OPENAI_BASE_URL: str = "https://api.siliconflow.cn/v1"
    OPENAI_MODEL: str = "Qwen/Qwen3.6-35B-A3B"

    # CORS 配置
    ALLOWED_ORIGINS: str = "http://localhost:3000"

    # 路径配置
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    MODELS_DIR: Path = Path(__file__).resolve().parent.parent.parent / "data" / "models"
    LOGS_DIR: Path = Path(__file__).resolve().parent.parent.parent / "logs"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        """PostgreSQL 连接串（同步，psycopg2）。"""
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @computed_field
    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @computed_field
    @property
    def CORS_ORIGINS_LIST(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]


# 全局单例
settings = Settings()