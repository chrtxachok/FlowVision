"""
API маршруты OCR сервиса.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel

from .schemas import (
    OCRTaskRequest,
    OCRTaskResponse,
    OCRTaskStatusResponse,
)

logger = structlog.get_logger()

router = APIRouter()

# Хранилище задач (в реальном приложении использовать Redis)
tasks_storage: dict = {}


class TaskStatus(BaseModel):
    """Статус задачи."""
    task_id: str
    status: str
    result: Optional[dict] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


@router.post("/ocr/tasks", response_model=OCRTaskResponse)
async def create_ocr_task(
    request: OCRTaskRequest,
    background_tasks: BackgroundTasks,
) -> OCRTaskResponse:
    """
    Создание новой задачи OCR обработки.
    
    Параметры:
        request: Параметры задачи
        background_tasks: Фоновые задачи FastAPI
        
    Returns:
        Информация о созданной задаче
    """
    task_id = str(uuid.uuid4())
    
    logger.info(
        "Creating OCR task",
        task_id=task_id,
        file_url=request.file_url,
        document_type=request.document_type,
    )
    
    # Создаем задачу
    task = TaskStatus(
        task_id=task_id,
        status="pending",
        created_at=datetime.utcnow(),
    )
    tasks_storage[task_id] = task
    
    # Запускаем фоновую обработку
    from ..workers.celery_tasks import process_document
    process_document.delay(task_id, request.file_url, request.document_type)
    
    return OCRTaskResponse(
        task_id=task_id,
        status="pending",
        message="Task created and queued for processing",
    )


@router.get("/ocr/tasks/{task_id}", response_model=OCRTaskStatusResponse)
async def get_task_status(task_id: str) -> OCRTaskStatusResponse:
    """
    Получение статуса задачи OCR.
    
    Параметры:
        task_id: ID задачи
        
    Returns:
        Статус задачи и результат (если готов)
    """
    task = tasks_storage.get(task_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    
    return OCRTaskStatusResponse(
        task_id=task.task_id,
        status=task.status,
        result=task.result,
        error_message=task.error_message,
        created_at=task.created_at,
        completed_at=task.completed_at,
    )


@router.delete("/ocr/tasks/{task_id}")
async def cancel_task(task_id: str) -> dict:
    """
    Отмена задачи OCR.
    
    Параметры:
        task_id: ID задачи
        
    Returns:
        Подтверждение отмены
    """
    task = tasks_storage.get(task_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )
    
    if task.status in ("completed", "failed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel task with status {task.status}",
        )
    
    task.status = "cancelled"
    tasks_storage[task_id] = task
    
    logger.info("Task cancelled", task_id=task_id)
    
    return {"message": "Task cancelled", "task_id": task_id}


@router.get("/ocr/supported-types")
async def get_supported_types() -> dict:
    """
    Получение списка поддерживаемых типов документов.
    
    Returns:
        Список поддерживаемых типов
    """
    return {
        "document_types": [
            {"id": "transport_waybill", "name": "Транспортная накладная"},
            {"id": "bill_of_lading", "name": "Коносамент"},
            {"id": "invoice", "name": "Счет-фактура"},
            {"id": "packing_list", "name": "Упаковочный лист"},
            {"id": "custom_declaration", "name": "Таможенная декларация"},
            {"id": "driver_license", "name": "Водительское удостоверение"},
            {"id": "vehicle_registration", "name": "Регистрация ТС"},
        ],
        "languages": ["ru", "en", "de", "fr", "es", "zh", "ja"],
    }


@router.post("/ocr/sync")
async def process_document_sync(request: OCRTaskRequest) -> dict:
    """
    Синхронная обработка документа.
    
    Использовать для small документов, время обработки < 30 сек.
    
    Параметры:
        request: Параметры обработки
        
    Returns:
        Результат обработки
    """
    logger.info(
        "Starting synchronous OCR",
        file_url=request.file_url,
        document_type=request.document_type,
    )
    
    try:
        from ..ocr.pipeline import OCRPipeline
        pipeline = OCRPipeline()
        result = pipeline.process(request.file_url)
        
        return {
            "status": "completed",
            "result": result,
        }
    except Exception as e:
        logger.error("OCR processing failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR processing failed: {str(e)}",
        )
