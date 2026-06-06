from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from typing import Optional, List
from pathlib import Path
import logging

from app.config import settings
from app.services.ocr_service import OCRService
from app.base_models.request import OCRRequest
from app.base_models.response import OCRResponse, ErrorResponse
from app.api.donut_routes import router as donut_router, initialize_donut

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
    
    # Инициализация Donut (если включена)
    try:
        initialize_donut()
    except Exception as e:
        logger.warning(f"Donut initialization deferred: {e}")
    
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

# Монтирование статических файлов
STATIC_DIR = Path(__file__).parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Главная страница
@app.get("/")
async def index():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Welcome to FlowLogix OCR Service"}

# Подключение Donut API
app.include_router(donut_router)

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ocr"}

# Допустимые форматы изображений (logika.py работает только с изображениями)
_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/bmp", "image/tiff"}


def _validate_upload(file: UploadFile) -> None:
    """Проверяет тип и размер загруженного изображения."""
    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. "
                   f"Поддерживаются: {', '.join(sorted(_ALLOWED_CONTENT_TYPES))}",
        )
    if file.size is not None and file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")


# Основной эндпоинт обработки.
#
# Полностью повторяет pipeline test_gui.py:
#   extractor.extract([page1])            — одна страница (автоопределение)
#   extractor.extract([page1, page2])     — первая и вторая страницы
#
# Принимает 1 (обязательно) или 2 (опционально) изображения накладной.
@app.post("/api/v1/ocr/process", response_model=OCRResponse)
async def process_document(
    file: UploadFile = File(..., description="Страница 1 (или единственная)"),
    file2: Optional[UploadFile] = File(None, description="Страница 2 (опционально)"),
    document_type: str = Form("waybill"),
    api_key: Optional[str] = Form(None),
):
    """
    Распознаёт накладную через logika.WaybillExtractor (тот же движок, что и в test_gui.py).

    - `file` — обязательная первая (или единственная) страница.
    - `file2` — необязательная вторая страница.
    """
    try:
        # Валидация ключа
        if api_key != settings.API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")

        # Валидация и чтение файлов (1 или 2 изображения)
        _validate_upload(file)
        files: List[tuple] = [(await file.read(), file.filename or "page1.jpg")]

        if file2 is not None and file2.filename:
            _validate_upload(file2)
            files.append((await file2.read(), file2.filename or "page2.jpg"))

        # Обработка через WaybillExtractor — тот же вызов, что и extractor.extract(paths)
        ocr_service: OCRService = app.state.ocr_service
        result = await ocr_service.process_document(
            files=files,
            document_type=document_type,
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR processing error: {e}", exc_info=True)
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
        "engine": "logika.WaybillExtractor (EasyOCR + ROI + RandomForest)",
        "supported_types": ["waybill"],
        "supported_formats": sorted(_ALLOWED_CONTENT_TYPES),
        "max_pages": 2,
        "max_file_size_mb": settings.MAX_FILE_SIZE / (1024 * 1024),
        "version": "1.0.0"
    }


