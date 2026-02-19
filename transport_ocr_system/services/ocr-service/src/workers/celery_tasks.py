"""
Celery задачи для асинхронной обработки OCR.
"""

import logging
import time
from typing import Optional

import structlog
from celery import Celery

# Конфигурация Celery
celery_app = Celery(
    "ocr_service",
    broker="redis://redis:6379/1",
    backend="redis://redis:6379/2",
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 час
    task_soft_time_limit=3300,  # 55 минут
    worker_prefetch_multiplier=1,
)

logger = structlog.get_logger()


@celery_app.task(bind=True, name="process_document")
def process_document(
    self,
    task_id: str,
    file_url: str,
    document_type: Optional[str] = None,
):
    """
    Обработка документа через OCR пайплайн.
    
    Args:
        task_id: ID задачи
        file_url: URL файла в MinIO
        document_type: Тип документа
        
    Returns:
        Результат обработки
    """
    start_time = time.time()
    
    logger.info(
        "Starting document processing",
        task_id=task_id,
        file_url=file_url,
        document_type=document_type,
    )
    
    try:
        # Обновление статуса задачи
        update_task_status(task_id, "processing", None)
        
        # Загрузка файла из MinIO
        from ..storage.minio_client import MinioClient
        from ..ocr.pipeline import OCRPipeline
        
        # Получение MinIO клиента (в реальном приложении использовать dependency injection)
        minio_client = MinioClient(
            endpoint="minio:9000",
            access_key="minioadmin",
            secret_key="minioadmin",
            bucket="documents",
        )
        
        # Скачивание файла
        object_name = file_url.replace("minio://documents/", "")
        file_data = minio_client.download_file(object_name)
        
        # Сохранение во временный файл
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            tmp_file.write(file_data)
            tmp_path = tmp_file.name
        
        try:
            # Запуск OCR пайплайна
            pipeline = OCRPipeline()
            result = pipeline.process(tmp_path)
            
            processing_time = time.time() - start_time
            
            if result.get("status") == "completed":
                update_task_status(
                    task_id, 
                    "completed", 
                    result,
                    processing_time=processing_time
                )
                logger.info(
                    "Document processing completed",
                    task_id=task_id,
                    processing_time=processing_time,
                )
            else:
                update_task_status(
                    task_id,
                    "failed",
                    None,
                    error_message=result.get("error", "Unknown error"),
                )
                logger.error(
                    "Document processing failed",
                    task_id=task_id,
                    error=result.get("error"),
                )
                
        finally:
            # Удаление временного файла
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        
        return result
        
    except Exception as e:
        logger.error(
            "Document processing error",
            task_id=task_id,
            error=str(e),
        )
        update_task_status(
            task_id,
            "failed",
            None,
            error_message=str(e),
        )
        raise


@celery_app.task(name="process_batch")
def process_batch(
    file_urls: list,
    document_types: Optional[list] = None,
):
    """
    Пакетная обработка документов.
    
    Args:
        file_urls: Список URL файлов
        document_types: Список типов документов
        
    Returns:
        Список результатов
    """
    results = []
    
    for i, file_url in enumerate(file_urls):
        doc_type = document_types[i] if document_types else None
        task_id = f"batch_{i}_{int(time.time())}"
        
        result = process_document.apply_async(
            args=[task_id, file_url, doc_type]
        )
        results.append(result.id)
    
    return results


def update_task_status(
    task_id: str,
    status: str,
    result: Optional[dict] = None,
    error_message: Optional[str] = None,
    processing_time: Optional[float] = None,
):
    """
    Обновление статуса задачи в хранилище.
    
    В реальном приложении использовать Redis или базу данных.
    """
    from ..api.routes import tasks_storage
    from datetime import datetime
    
    if task_id in tasks_storage:
        task = tasks_storage[task_id]
        task.status = status
        task.completed_at = datetime.utcnow()
        
        if result:
            task.result = result
        if error_message:
            task.error_message = error_message
            
        tasks_storage[task_id] = task
