from pydantic_settings import BaseSettings
from typing import List
from pathlib import Path

class Settings(BaseSettings):
    """Конфигурация сервиса"""
    
    # Основные настройки
    API_KEY: str = "dev-secret-key-change-in-production"
    DEBUG: bool = False
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:8000",
        "https://your-crm-domain.ru"
    ]
    
    # Ограничения
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB
    MAX_IMAGE_DIMENSION: int = 4096
    
    # Пути к моделям
    MODEL_DIR: Path = Path(__file__).parent.parent / "models"
    DETECT_MODEL_PATH: Path = MODEL_DIR / "paddle_det"
    RECOGNIZE_MODEL_PATH: Path = MODEL_DIR / "paddle_rec"
    
    # Настройки обработки
    CONFIDENCE_THRESHOLD: float = 0.7
    LANGUAGE: str = "ru"
    
    # Логирование
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()