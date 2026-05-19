import os
from pathlib import Path
from typing import List, Dict

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
    ALLOWED_ORIGINS: List[str] = [
        # "http://localhost:8000",
        # "https://your-crm-domain.ru"
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

    # OCR backend
    # easyocr: проще установка/использование, модели скачиваются автоматически
    # paddleocr: остаётся как альтернативный вариант (локальные модели + scripts/download_models.py)
    OCR_BACKEND: str = "easyocr"  # "easyocr" | "paddleocr"
    OCR_DEVICE: str = "cpu"  # "cpu" | "gpu"

    # EasyOCR settings
    # Список языков EasyOCR (ISO-639-1). Для РФ накладных обычно хватает ru+en.
    EASYOCR_LANGUAGES: List[str] = ["ru", "en"]
    
    # Donut model settings
    DONUT_ENABLED: bool = True
    DONUT_MODEL_NAME: str = "naver-clova-ocr/donut-base"
    # Для локальной модели укажите путь: "models/donut-base"
    DONUT_CACHE_DIR: Path = MODEL_DIR
    DONUT_DEVICE: str = "cpu"  # "cpu" | "cuda"
    
    # Task prompts для разных типов документов в Donut
    DONUT_TASK_PROMPTS: Dict[str, str] = {
        "waybill": "<s_waybill>",
        "invoice": "<s_invoice>",
        "act": "<s_act>",
        "upd": "<s_upd>",
    }
    
    # Параметры генерации для Donut
    DONUT_MAX_LENGTH: int = 384
    DONUT_NUM_BEAMS: int = 1
    DONUT_TEMPERATURE: float = 1.0
    
    # Логирование
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

settings = Settings()