"""
API endpoints для работы с Donut моделью.

Эндпоинты:
- POST /api/v1/donut/extract — синхронное извлечение данных из документа
- GET /api/v1/donut/info — информация о модели
- POST /api/v1/donut/parse-json — парсинг JSON результата Donut
"""

from fastapi import APIRouter, File, UploadFile, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
import logging
import time
import io
import json
from typing import Optional, Dict, Any
from PIL import Image

from app.config import settings
from app.ocr.donut_extractor import DonutExtractor
from app.ocr.preprocess import bytes_to_numpy, enhance_image
from app.base_models.response import OCRResponse, ProcessingStatus, ErrorResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/donut", tags=["donut"])

# Глобальный extractor (инициализируется один раз)
_donut_extractor: Optional[DonutExtractor] = None


def get_donut_extractor() -> DonutExtractor:
    """
    Получает или инициализирует Donut extractor.
    Используется как dependency в эндпоинтах.
    """
    global _donut_extractor
    
    if _donut_extractor is None:
        if not settings.DONUT_ENABLED:
            raise HTTPException(
                status_code=503,
                detail="Donut model is disabled in settings"
            )
        
        try:
            logger.info("Инициализирую Donut extractor...")
            _donut_extractor = DonutExtractor.from_pretrained(
                model_name_or_path=settings.DONUT_MODEL_NAME,
                device=settings.DONUT_DEVICE,
                cache_dir=settings.DONUT_CACHE_DIR,
            )
            logger.info("✓ Donut extractor готов к работе")
        except Exception as e:
            logger.error(f"Ошибка при инициализации Donut: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize Donut model: {str(e)}"
            )
    
    return _donut_extractor


@router.post("/extract", response_model=OCRResponse)
async def extract_with_donut(
    file: UploadFile = File(...),
    document_type: str = Query("invoice", description="Тип документа: waybill, invoice, act, upd"),
    extractor: DonutExtractor = Depends(get_donut_extractor),
) -> OCRResponse:
    """
    Извлечение структурированных данных из документа с помощью Donut.

    Parameters
    ----------
    file : UploadFile
        Загруженный файл (JPEG, PNG, PDF)
    document_type : str
        Тип документа для выбора task_prompt
    
    Returns
    -------
    OCRResponse
        Результат обработки с извлеченными данными
    """
    start_time = time.time()
    
    try:
        # Валидация файла
        if file.content_type not in ["image/jpeg", "image/png", "application/pdf"]:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file.content_type}. "
                       "Supported: image/jpeg, image/png, application/pdf"
            )
        
        if file.size and file.size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {file.size} bytes (max: {settings.MAX_FILE_SIZE})"
            )
        
        # Чтение файла
        file_bytes = await file.read()
        
        # Конвертация в numpy array
        try:
            image_array = bytes_to_numpy(file_bytes, file.content_type)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to process image: {str(e)}"
            )
        
        # Улучшение изображения для лучшего результата
        image_array = enhance_image(image_array)
        
        # Выбор task prompt
        task_prompt = settings.DONUT_TASK_PROMPTS.get(
            document_type,
            settings.DONUT_TASK_PROMPTS.get("invoice", "<s_invoice>")
        )
        
        # Извлечение данных
        logger.info(f"Запускаю Donut для документа типа '{document_type}'...")
        result = extractor.extract(
            image=image_array,
            task_prompt=task_prompt,
            max_length=settings.DONUT_MAX_LENGTH,
            num_beams=settings.DONUT_NUM_BEAMS,
            temperature=settings.DONUT_TEMPERATURE,
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Парсинг выходных данных Donut
        extracted_data = _parse_donut_output(result["text"], document_type)
        
        return OCRResponse(
            status=ProcessingStatus.SUCCESS,
            document_type=document_type,
            confidence=result.get("confidence", 0.95),
            processing_time_ms=processing_time,
            extracted_data=extracted_data,
            raw_text=result.get("text", ""),
            metadata={
                **result.get("metadata", {}),
                "model_type": "donut",
                "file_name": file.filename,
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обработке документа: {e}", exc_info=True)
        processing_time = int((time.time() - start_time) * 1000)
        
        return OCRResponse(
            status=ProcessingStatus.FAILED,
            document_type=document_type,
            confidence=0.0,
            processing_time_ms=processing_time,
            extracted_data={},
            metadata={"error": str(e)}
        )


@router.get("/info")
async def get_donut_info(
    extractor: DonutExtractor = Depends(get_donut_extractor),
) -> Dict[str, Any]:
    """
    Информация о загруженной Donut модели.
    """
    return {
        "model": str(extractor.model_path),
        "device": extractor.device,
        "task_prompt_default": extractor.task_prompt,
        "supported_document_types": list(settings.DONUT_TASK_PROMPTS.keys()),
        "generation_params": {
            "max_length": settings.DONUT_MAX_LENGTH,
            "num_beams": settings.DONUT_NUM_BEAMS,
            "temperature": settings.DONUT_TEMPERATURE,
        },
        "supported_formats": ["image/jpeg", "image/png", "application/pdf"],
        "max_file_size_mb": settings.MAX_FILE_SIZE / (1024 * 1024),
    }


@router.post("/parse-json")
async def parse_donut_json(
    raw_output: str = Query(..., description="Сырой output от Donut модели"),
    document_type: str = Query("invoice", description="Тип документа"),
) -> Dict[str, Any]:
    """
    Парсинг JSON результата Donut.
    
    Используется для тестирования парсинга без повторного выполнения модели.
    """
    try:
        parsed = _parse_donut_output(raw_output, document_type)
        return {
            "success": True,
            "document_type": document_type,
            "extracted_data": parsed,
        }
    except Exception as e:
        logger.error(f"Ошибка при парсинге JSON: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to parse JSON output: {str(e)}"
        )


# ------------------------------------------------------------------
# Вспомогательные функции
# ------------------------------------------------------------------

def _parse_donut_output(raw_output: str, document_type: str) -> Dict[str, Any]:
    """
    Парсит raw output от Donut модели в структурированные данные.
    
    Donut обычно выводит в формате:
    <s_invoice> ... </s_invoice>
    или JSON внутри специальных тегов.
    
    Parameters
    ----------
    raw_output : str
        Сырой output от Donut модели
    document_type : str
        Тип документа для правильной интерпретации
        
    Returns
    -------
    dict
        Структурированные данные
    """
    try:
        # Попытка парсить как JSON
        # Ищем первый '{' и последний '}'
        start_idx = raw_output.find('{')
        end_idx = raw_output.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            json_str = raw_output[start_idx:end_idx + 1]
            try:
                data = json.loads(json_str)
                logger.debug(f"Успешно распарсен JSON из Donut output")
                return data
            except json.JSONDecodeError:
                logger.warning(f"JSON парсинг не удался, используем raw text")
        
        # Fallback: возвращаем raw text в структурированном виде
        return {
            "raw_text": raw_output,
            "document_type": document_type,
            "parsing_status": "raw_text_fallback",
        }
        
    except Exception as e:
        logger.error(f"Ошибка при парсинге Donut output: {e}")
        return {
            "error": str(e),
            "raw_text": raw_output[:500],  # First 500 chars
        }


def initialize_donut():
    """Инициализирует Donut при старте приложения."""
    global _donut_extractor
    
    if not settings.DONUT_ENABLED:
        logger.info("Donut отключён в конфигурации")
        return
    
    try:
        logger.info("Инициализирую Donut при старте приложения...")
        _donut_extractor = DonutExtractor.from_pretrained(
            model_name_or_path=settings.DONUT_MODEL_NAME,
            device=settings.DONUT_DEVICE,
            cache_dir=settings.DONUT_CACHE_DIR,
        )
        logger.info("✓ Donut успешно загружена")
    except Exception as e:
        logger.warning(f"Не удалось загрузить Donut: {e}. "
                      "Эндпоинты будут инициализировать модель при первом запросе.")
