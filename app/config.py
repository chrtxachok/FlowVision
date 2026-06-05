# app/config.py
import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings

# Базовая директория проекта
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    """Конфигурация сервиса"""
    
    # Основные настройки
    API_KEY: str = "dev-secret-key-change-in-production"
    DEBUG: bool = False
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # Ограничения
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB
    MAX_IMAGE_DIMENSION: int = 4096
    
    # Пути к моделям
    MODEL_DIR: Path = BASE_DIR / "models"
    
    # imitation_model файлы (обученные через train_model_from_json)
    LEGACY_CLASSIFIER_PATH: Path = MODEL_DIR / "field_classifier.pkl"
    LEGACY_SCALER_PATH: Path = MODEL_DIR / "scaler.pkl"
    LEGACY_COORDS_PATH: Path = MODEL_DIR / "field_coords.pkl"
    
    # Настройки обработки
    CONFIDENCE_THRESHOLD: float = 0.7
    LANGUAGE: str = "ru"
    
    # OCR backend — только EasyOCR для imitation_model
    OCR_BACKEND: str = "easyocr"
    OCR_DEVICE: str = "cpu"
    EASYOCR_LANGUAGES: List[str] = ["ru", "en"]
    
    # Логирование
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Path = BASE_DIR / "logs" / "app.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

settings = Settings()