"""Application configuration"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings"""
    
    # API Settings
    APP_NAME: str = "NeuroSkate AI"
    DEBUG: bool = True
    API_V1_STR: str = "/api"
    
    # Security
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database
    DATABASE_URL: str = "postgresql://neuroskate:neuroskate_pass@localhost:5432/neuroskate"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # AWS S3
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = "neuroskate-videos"
    S3_REGION: str = "us-east-1"
    
    # Computer Vision
    CV_MODEL_PATH: str = "models/trick_classifier.pth"
    CV_MIN_CONFIDENCE: float = 0.75
    CV_FRAME_SKIP: int = 2  # Process every Nth frame
    
    # Video Processing
    MAX_VIDEO_SIZE_MB: int = 100
    ALLOWED_VIDEO_FORMATS: List[str] = ["mp4", "mov", "avi"]
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://localhost:8080",
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()