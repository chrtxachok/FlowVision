"""Views for documents app."""

import logging
import requests
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from .models import Document, DocumentField, DocumentTable, ProcessingStatus
from .serializers import (
    DocumentSerializer,
    DocumentDetailSerializer,
    DocumentUploadSerializer,
    DocumentFieldSerializer,
)

logger = logging.getLogger(__name__)


class DocumentViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с документами."""
    
    queryset = Document.objects.all()
    serializer_class = DocumentSerializer
    parser_classes = (MultiPartParser, FormParser)
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'document_type']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DocumentDetailSerializer
        if self.action == 'create':
            return DocumentUploadSerializer
        return DocumentSerializer
    
    def create(self, request, *args, **kwargs):
        """Загрузка нового документа."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Сохранение документа
        document = serializer.save()
        
        # Запуск OCR обработки
        self._start_ocr_processing(document)
        
        logger.info(f"Document uploaded: {document.id}")
        
        return Response(
            DocumentSerializer(document).data,
            status=status.HTTP_201_CREATED
        )
    
    def _start_ocr_processing(self, document: Document):
        """Запуск OCR обработки документа."""
        try:
            # Загрузка файла в MinIO и получение URL
            from minio import Minio
            
            minio_client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )
            
            # Создание бакета если не существует
            if not minio_client.bucket_exists(settings.MINIO_BUCKET):
                minio_client.make_bucket(settings.MINIO_BUCKET)
            
            # Загрузка файла
            file_path = document.file.path
            object_name = f"{document.id}/{document.filename}"
            minio_client.fput_object(
                settings.MINIO_BUCKET,
                object_name,
                file_path
            )
            
            # Вызов OCR сервиса
            ocr_url = f"{settings.OCR_SERVICE_URL}/api/v1/ocr/tasks"
            response = requests.post(
                ocr_url,
                json={
                    "file_url": f"minio://{settings.MINIO_BUCKET}/{object_name}",
                    "document_type": document.document_type,
                }
            )
            
            if response.status_code == 200:
                task_data = response.json()
                document.ocr_task_id = task_data.get("task_id")
                document.status = ProcessingStatus.QUEUED
                document.save()
                
                logger.info(f"OCR task created: {document.ocr_task_id}")
            else:
                logger.error(f"OCR service error: {response.text}")
                document.status = ProcessingStatus.FAILED
                document.error_message = "Failed to create OCR task"
                document.save()
                
        except Exception as e:
            logger.error(f"Error starting OCR processing: {str(e)}")
            document.status = ProcessingStatus.FAILED
            document.error_message = str(e)
            document.save()
    
    @action(detail=True, methods=['post'])
    def reprocess(self, request, pk=None):
        """Повторная обработка документа."""
        document = self.get_object()
        document.status = ProcessingStatus.PENDING
        document.error_message = ''
        document.save()
        
        self._start_ocr_processing(document)
        
        return Response({'status': 'Processing restarted'})
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Получение статистики по документам."""
        stats = {
            'total': Document.objects.count(),
            'pending': Document.objects.filter(status=ProcessingStatus.PENDING).count(),
            'queued': Document.objects.filter(status=ProcessingStatus.QUEUED).count(),
            'processing': Document.objects.filter(status=ProcessingStatus.PROCESSING).count(),
            'completed': Document.objects.filter(status=ProcessingStatus.COMPLETED).count(),
            'failed': Document.objects.filter(status=ProcessingStatus.FAILED).count(),
        }
        return Response(stats)
    
    @action(detail=True, methods=['get'])
    def check_status(self, request, pk=None):
        """Проверка статуса обработки документа."""
        document = self.get_object()
        
        if document.ocr_task_id:
            try:
                # Запрос статуса у OCR сервиса
                ocr_url = f"{settings.OCR_SERVICE_URL}/api/v1/ocr/tasks/{document.ocr_task_id}"
                response = requests.get(ocr_url)
                
                if response.status_code == 200:
                    task_data = response.json()
                    document.status = task_data.get('status', document.status)
                    
                    if task_data.get('result'):
                        document.extracted_data = task_data['result'].get('extracted_data')
                        document.raw_text = task_data['result'].get('raw_text')
                        document.processing_time = task_data['result'].get('processing_time')
                    
                    if task_data.get('error_message'):
                        document.error_message = task_data['error_message']
                    
                    document.save()
                    
            except Exception as e:
                logger.error(f"Error checking OCR status: {str(e)}")
        
        return Response(DocumentSerializer(document).data)


class DocumentFieldViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для работы с полями документа."""
    
    serializer_class = DocumentFieldSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['document', 'field_type']
    
    def get_queryset(self):
        return DocumentField.objects.select_related('document').all()
