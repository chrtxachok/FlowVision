"""
Главный модуль OCR сервиса (FastAPI приложение).
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router as api_router
from .api.schemas import HealthCheckResponse
from .storage.minio_client import MinioClient

# Настройка структурированного логирования
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Загрузка конфигурации
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Управление жизненным циклом приложения."""
    # Startup
    logger.info("Starting OCR service", version=config["service"]["version"])
    
    # Инициализация MinIO клиента
    storage_config = config["storage"]
    minio_client = MinioClient(
        endpoint=storage_config["endpoint"],
        access_key=storage_config["access_key"],
        secret_key=storage_config["secret_key"],
        bucket=storage_config["bucket"],
        secure=storage_config.get("secure", False),
    )
    app.state.minio_client = minio_client
    
    # Проверка доступности MinIO
    try:
        minio_client.check_connection()
        logger.info("MinIO connection established")
    except Exception as e:
        logger.warning("MinIO connection failed", error=str(e))
    
    yield
    
    # Shutdown
    logger.info("Shutting down OCR service")


# Создание FastAPI приложения
app = FastAPI(
    title="OCR Service",
    description="Микросервис для оптического распознавания текста транспортных документов",
    version=config["service"]["version"],
    lifespan=lifespan,
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(api_router, prefix="/api/v1", tags=["OCR"])


@app.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """Проверка здоровья сервиса."""
    return HealthCheckResponse(
        status="healthy",
        version=config["service"]["version"],
    )


@app.get("/")
async def root() -> dict:
    """Корневой эндпоинт."""
    return {
        "service": "OCR Service",
        "version": config["service"]["version"],
        "status": "running",
    }
