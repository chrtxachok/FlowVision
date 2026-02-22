from celery import shared_task
from celery.utils.log import get_task_logger
import time
import os

from api.dependencies import get_settings
from storage.minio_client import MinioClient
from monitoring.metrics import record_processing_time, increment_failures_counter

logger = get_task_logger(__name__)

# Глобальный пайплайн (загружается один раз)
_pipeline = None


def get_pipeline():
    """Lazy loading of OCR pipeline"""
    global _pipeline
    if _pipeline is None:
        from ocr.pipeline import LayoutLMPipeline
        settings = get_settings()
        
        logger.info("Initializing LayoutLM pipeline...")
        _pipeline = LayoutLMPipeline(
            model_path=settings.LAYOUTLM_MODEL_PATH,
            device=settings.DEVICE
        )
        _pipeline.load_models()
        logger.info("LayoutLM pipeline initialized")
    
    return _pipeline


@shared_task(bind=True, max_retries=3)
def process_document_task(self, task_id: str, document_id: str, 
                         file_path: str, document_type: str):
    """
    Asynchronous OCR processing task
    
    Args:
        task_id: Unique task identifier
        document_id: External document identifier
        file_path: Local path to downloaded file
        document_type: Type of document
    """
    start_time = time.time()
    settings = get_settings()
    
    try:
        logger.info(f"Starting OCR processing for document {document_id}")
        
        # Get pipeline
        pipeline = get_pipeline()
        
        # Process document
        result = pipeline.process_document(file_path, document_id)
        
        # Calculate processing time
        processing_time = time.time() - start_time
        record_processing_time(document_type, processing_time)
        
        logger.info(f"Document {document_id} processed in {processing_time:.2f}s")
        
        # Clean up temporary file
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # Prepare response
        return {
            'document_id': document_id,
            'task_id': task_id,
            'status': 'success',
            'processing_time': processing_time,
            'data': result.extracted_data,
            'confidence': result.confidence_scores,
            'raw_text': result.raw_text
        }
        
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}", exc_info=True)
        increment_failures_counter(document_type)
        
        # Retry on transient errors
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task {task_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
        
        # Final failure
        return {
            'document_id': document_id,
            'task_id': task_id,
            'status': 'failed',
            'error': str(e)
        }


@shared_task
def cleanup_temp_files():
    """Periodic task to clean up temporary files"""
    temp_dir = '/tmp/ocr_processing'
    if os.path.exists(temp_dir):
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            try:
                if os.path.isfile(file_path):
                    file_age = time.time() - os.path.getmtime(file_path)
                    if file_age > 3600:  # Delete files older than 1 hour
                        os.remove(file_path)
                        logger.info(f"Cleaned up {file_path}")
            except Exception as e:
                logger.error(f"Error cleaning up {file_path}: {e}")