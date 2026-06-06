# app/config.py
import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings

os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_HUB_OFFLINE'] = '1'

# Базовая директория проекта
BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    """Конфигурация сервиса"""
    
    # Основные настройки
    API_KEY: str = "dev-secret-key-change-in-production"
    DEBUG: bool = False
    
    # CORS
    ALLOWED_ORIGINS: str = "*"
    
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
    
    # Donut model settings
    DONUT_ENABLED: bool = True
    DONUT_MODEL_NAME: str = "models/donut-base"  # ← локальный путь вместо HuggingFace
    # Для локальной модели укажите путь: "models/donut-base"
    DONUT_CACHE_DIR: Path = MODEL_DIR
    DONUT_DEVICE: str = "cpu"  # "cpu" | "cuda"
    '''
    # Task prompts для разных типов документов в Donut
    DONUT_TASK_PROMPTS: Dict[str, str] = {
        "waybill": "<s_waybill>",
        "invoice": "<s_invoice>",
        "act": "<s_act>",
        "upd": "<s_upd>",
    }
    '''
    # Параметры генерации для Donut
    DONUT_MAX_LENGTH: int = 768  # Увеличено для полного JSON результата
    DONUT_NUM_BEAMS: int = 1
    DONUT_TEMPERATURE: float = 1.0
    
    # Логирование
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Path = BASE_DIR / "logs" / "app.log"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

settings = Settings()
