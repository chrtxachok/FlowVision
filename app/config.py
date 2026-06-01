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
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:8000",
        "https://your-crm-domain.ru"
    ]
    
    # Ограничения
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB
    MAX_IMAGE_DIMENSION: int = 4096
    
    # Пути к моделям (должны совпадать с именами папок после распаковки скриптами загрузки)
    MODEL_DIR: Path = Path(__file__).parent.parent / "models"
    DETECT_MODEL_PATH: Path = MODEL_DIR / "en_PP-OCRv4_det_infer"
    RECOGNIZE_MODEL_PATH: Path = MODEL_DIR / "Multilingual_PP-OCRv4_rec_infer"
    CLASSIFY_MODEL_PATH: Path = MODEL_DIR / "ch_ppocr_mobile_v2.0_cls_infer"

    # Если True — используем локальные модели; если False — PaddleOCR скачает их сам
    USE_LOCAL_MODELS: bool = True  

    # Настройки обработки
    CONFIDENCE_THRESHOLD: float = 0.7
    LANGUAGE: str = "ru"

    # OCR backend: easyocr | paddleocr | donut
    OCR_BACKEND: str = "donut"
    OCR_DEVICE: str = "cpu"  # "cpu" | "gpu"

    # Donut (дообученная модель)
    DONUT_MODEL_PATH: Path = MODEL_DIR / "donut-trained-final"
    DONUT_DEVICE: str = "cpu"  # cpu | cuda
    DONUT_MAX_LENGTH: int = 512
    DONUT_IMAGE_WIDTH: int = 1280
    DONUT_IMAGE_HEIGHT: int = 960
    DONUT_NUM_BEAMS: int = 4
    DONUT_REPETITION_PENALTY: float = 1.15

    # EasyOCR settings
    # Список языков EasyOCR (ISO-639-1). Для РФ накладных обычно хватает ru+en.
    EASYOCR_LANGUAGES: List[str] = ["ru", "en"]
    
    # Логирование
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()