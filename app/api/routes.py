from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from typing import Dict, Any, Optional
import logging
import uuid

from .schemas import (
    ProcessDocumentRequest,
    ProcessDocumentResponse,
    TaskStatusResponse,
    ErrorResponse
)
from .dependencies import verify_api_key, get_settings
from storage.minio_client import MinioClient
from app.workers.table_extractor import process_document_task
from monitoring.metrics import increment_requests_counter, record_processing_time

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/process",
    response_model=ProcessDocumentResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def process_document(
    request: ProcessDocumentRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key),
    settings = Depends(get_settings)
):
    """
    Process a document with OCR
    
    This endpoint initiates OCR processing of a document.
    The actual processing happens asynchronously.
    """
    try:
        increment_requests_counter(request.document_type)
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Download file from storage
        minio_client = MinioClient(settings)
        local_file_path = minio_client.download_file(request.file_path)
        
        # Start background processing
        task = process_document_task.delay(
            task_id=task_id,
            document_id=request.document_id,
            file_path=local_file_path,
            document_type=request.document_type
        )
        
        logger.info(f"Started processing task {task_id} for document {request.document_id}")
        
        return ProcessDocumentResponse(
            task_id=task_id,
            status="processing",
            message="Document processing started",
            document_id=request.document_id
        )
        
    except Exception as e:
        logger.error(f"Error processing document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get(
    "/tasks/{task_id}",
    response_model=TaskStatusResponse,
    responses={404: {"model": ErrorResponse}}
)
async def get_task_status(
    task_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Get the status of a processing task"""
    
    from celery.result import AsyncResult
    from workers.celery_app import celery_app
    
    task_result = AsyncResult(task_id, app=celery_app)
    
    if task_result.state == 'PENDING':
        return TaskStatusResponse(
            task_id=task_id,
            status="pending",
            progress=0
        )
    elif task_result.state == 'STARTED':
        return TaskStatusResponse(
            task_id=task_id,
            status="processing",
            progress=50
        )
    elif task_result.state == 'SUCCESS':
        result = task_result.result
        return TaskStatusResponse(
            task_id=task_id,
            status="completed",
            progress=100,
            result=result
        )
    elif task_result.state == 'FAILURE':
        return TaskStatusResponse(
            task_id=task_id,
            status="failed",
            progress=100,
            error=str(task_result.info)
        )
    else:
        return TaskStatusResponse(
            task_id=task_id,
            status=task_result.state.lower(),
            progress=0
        )


@router.post(
    "/process/sync",
    response_model=ProcessDocumentResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def process_document_sync(
    request: ProcessDocumentRequest,
    api_key: str = Depends(verify_api_key),
    settings = Depends(get_settings)
):
    """
    Process a document synchronously (for testing/small files)
    
    ⚠️ This will block until processing is complete
    """
    try:
        from ocr.pipeline import LayoutLMPipeline
        
        # Download file
        minio_client = MinioClient(settings)
        local_file_path = minio_client.download_file(request.file_path)
        
        # Process document
        pipeline = LayoutLMPipeline(
            model_path=settings.LAYOUTLM_MODEL_PATH,
            device=settings.DEVICE
        )
        pipeline.load_models()
        
        result = pipeline.process_document(local_file_path, request.document_id)
        
        # Upload result back to storage if needed
        # ...
        
        return ProcessDocumentResponse(
            task_id=str(uuid.uuid4()),
            status="completed",
            message="Document processed successfully",
            document_id=request.document_id,
            result=result.__dict__
        )
        
    except Exception as e:
        logger.error(f"Error processing document: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )