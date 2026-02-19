from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # Server settings
    DEBUG: bool = os.getenv('DEBUG', 'False') == 'True'
    PORT: int = int(os.getenv('PORT', '8001'))
    HOST: str = os.getenv('HOST', '0.0.0.0')
    WORKERS: int = int(os.getenv('WORKERS', '4'))
    
    # Security
    API_KEY: str = os.getenv('API_KEY', 'your-secret-key')
    
    # ML Models
    LAYOUTLM_MODEL_PATH: str = os.getenv(
        'LAYOUTLM_MODEL_PATH',
        '/app/models/layoutlm'
    )
    DBNET_MODEL_PATH: str = os.getenv(
        'DBNET_MODEL_PATH',
        '/app/models/dbnet'
    )
    DEVICE: str = os.getenv('DEVICE', 'cuda' if os.getenv('USE_GPU') == 'True' else 'cpu')
    
    # Storage (MinIO/S3)
    MINIO_ENDPOINT: str = os.getenv('MINIO_ENDPOINT', 'minio:9000')
    MINIO_ACCESS_KEY: str = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
    MINIO_SECRET_KEY: str = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
    MINIO_BUCKET: str = os.getenv('MINIO_BUCKET', 'documents')
    MINIO_SECURE: bool = os.getenv('MINIO_SECURE', 'False') == 'True'
    
    # Redis (for Celery)
    REDIS_HOST: str = os.getenv('REDIS_HOST', 'redis')
    REDIS_PORT: int = int(os.getenv('REDIS_PORT', '6379'))
    REDIS_DB: int = int(os.getenv('REDIS_DB', '1'))
    
    # Celery
    CELERY_BROKER_URL: str = os.getenv(
        'CELERY_BROKER_URL',
        f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
    )
    CELERY_RESULT_BACKEND: str = os.getenv(
        'CELERY_RESULT_BACKEND',
        f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'
    )
    
    # Monitoring
    PROMETHEUS_ENABLED: bool = os.getenv('PROMETHEUS_ENABLED', 'True') == 'True'
    METRICS_PORT: int = int(os.getenv('METRICS_PORT', '8002'))
    
    class Config:
        env_file = ".env"
        case_sensitive = True


def get_settings() -> Settings:
    return Settings()