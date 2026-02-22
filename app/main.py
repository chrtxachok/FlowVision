from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from typing import Optional
import logging
from app.config import settings
from app.services.ocr_service import OCRService
from app.base_models.request import OCRRequest
from app.base_models.response import OCRResponse, ErrorResponse

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Жизненный цикл приложения
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Инициализация сервиса при запуске"""
    # Загрузка моделей
    logger.info("Loading OCR models...")
    ocr_service = OCRService()
    app.state.ocr_service = ocr_service
    logger.info("OCR service initialized")
    yield
    # Очистка при завершении
    logger.info("Shutting down OCR service")

app = FastAPI(
    title="FlowLogix OCR Service",
    description="Микросервис для распознавания накладных и документов",
    version="1.0.0",
    lifespan=lifespan
)

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ocr"}

# Основной эндпоинт обработки
@app.post("/api/v1/ocr/process", response_model=OCRResponse)
async def process_document(
    file: UploadFile = File(...),
    document_type: str = "waybill",
    api_key: Optional[str] = None
):
    """Обработка документа через OCR"""
    try:
        # Валидация ключа
        if api_key != settings.API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        # Валидация файла
        if not file.content_type in ["image/jpeg", "image/png", "application/pdf"]:
            raise HTTPException(status_code=400, detail="Unsupported file type")
        
        if file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")
        
        # Чтение файла
        file_bytes = await file.read()
        
        # Обработка
        ocr_service: OCRService = app.state.ocr_service
        result = await ocr_service.process_document(
            file_bytes=file_bytes,
            file_type=file.content_type,
            document_type=document_type
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR processing error: {e}")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="ocr_processing_failed",
                message=str(e)
            ).dict()
        )

# Информация о сервисе
@app.get("/api/v1/ocr/info")
async def get_service_info():
    return {
        "supported_types": ["waybill", "invoice", "act", "upd"],
        "supported_formats": ["image/jpeg", "image/png", "application/pdf"],
        "max_file_size_mb": settings.MAX_FILE_SIZE / (1024 * 1024),
        "version": "1.0.0"
    }