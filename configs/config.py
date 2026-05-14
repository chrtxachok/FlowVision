# src/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Базовая директория проекта
BASE_DIR = Path(__file__).resolve().parent.parent

# Пути к данным
LOCAL_MODEL_PATH = os.getenv("LOCAL_MODEL_PATH", "./models/donut-trained")
DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
LOGS_DIR = Path(os.getenv("LOGS_DIR", "./logs"))
CACHE_DIR = Path(os.getenv("CACHE_DIR", "./cache"))

# Настройки модели
INFERENCE_DEVICE = os.getenv("INFERENCE_DEVICE", "cpu")
MODEL_MAX_LENGTH = int(os.getenv("MODEL_MAX_LENGTH", "1024"))
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))

# Настройки API
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
API_WORKERS = int(os.getenv("API_WORKERS", "2"))

# Логирование
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = Path(os.getenv("LOG_FILE", "./logs/app.log"))

# Ограничения
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", "10485760"))
MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", "10"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "300"))

# HuggingFace offline режим
HF_DATASETS_OFFLINE = os.getenv("HF_DATASETS_OFFLINE", "1")
TRANSFORMERS_OFFLINE = os.getenv("TRANSFORMERS_OFFLINE", "1")

# Безопасность
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "dev-secret-key-change-in-production")
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

# Проверка что директории существуют
def ensure_directories():
    """Создаёт необходимые директории если их нет."""
    for dir_path in [DATA_DIR, LOGS_DIR, CACHE_DIR, Path(LOCAL_MODEL_PATH)]:
        dir_path.mkdir(parents=True, exist_ok=True)