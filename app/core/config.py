"""
企業級 AVP 配置管理
支持環境變數、密鑰管理、多環境配置
"""
from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache


class Settings(BaseSettings):
    """應用配置"""
    
    # 基礎配置
    APP_NAME: str = "Enterprise AI Video Production Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"  # development, staging, production
    
    # API 配置
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["*"]
    
    # 數據庫配置
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "avp"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "avp_platform"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Neo4j 配置
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""
    
    # Milvus 配置
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    
    # Redis 配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    
    # JWT 配置
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # 安全配置
    SECRET_KEY: str = ""  # Flask/FastAPI secret
    ENCRYPTION_KEY: str = ""  # 字段級加密密鑰
    
    # 存儲配置
    STORAGE_BACKEND: str = "local"  # local, s3, gcs, azure
    STORAGE_PATH: str = "./storage"
    MAX_UPLOAD_SIZE: int = 524288000  # 500MB
    MAX_VIDEO_DURATION: int = 300  # 5 minutes
    
    # AWS S3 配置
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    
    # 視頻生成配置
    VIDEO_DEFAULT_RESOLUTION: str = "1920x1080"
    VIDEO_MAX_RESOLUTION: str = "3840x2160"
    VIDEO_DEFAULT_FPS: int = 24
    VIDEO_DEFAULT_ASPECT_RATIO: str = "16:9"
    
    # GPU 資源配置
    GPU_POOL_SIZE: int = 4
    MAX_CONCURRENT_GENERATIONS: int = 10
    GENERATION_TIMEOUT_SECONDS: int = 600
    
    # 監控配置
    PROMETHEUS_ENABLED: bool = True
    PROMETHEUS_PORT: int = 9090
    LOG_LEVEL: str = "INFO"
    
    # AI 模型配置
    DEFAULT_VIDEO_MODEL: str = "stable-video-diffusion"
    DEFAULT_LLM_MODEL: str = "gpt-4"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # 內容安全配置
    CONTENT_SAFETY_ENABLED: bool = True
    AZURE_CONTENT_SAFETY_KEY: Optional[str] = None
    AZURE_CONTENT_SAFETY_ENDPOINT: Optional[str] = None
    
    # 水印配置
    WATERMARK_ENABLED: bool = True
    WATERMARK_C2PA_ENABLED: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """獲取配置單例"""
    return Settings()


# 快捷訪問
settings = get_settings()
