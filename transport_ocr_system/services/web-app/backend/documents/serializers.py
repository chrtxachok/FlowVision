"""Serializers for documents app."""

from rest_framework import serializers
from .models import Document, DocumentField, DocumentTable, DocumentType, ProcessingStatus


class DocumentFieldSerializer(serializers.ModelSerializer):
    """Serializer для полей документа."""
    
    class Meta:
        model = DocumentField
        fields = ['id', 'name', 'value', 'field_type', 'confidence', 'page_number']


class DocumentTableSerializer(serializers.ModelSerializer):
    """Serializer для таблиц документа."""
    
    class Meta:
        model = DocumentTable
        fields = ['id', 'table_id', 'page_number', 'headers', 'data']


class DocumentUploadSerializer(serializers.ModelSerializer):
    """Serializer для загрузки документа."""
    
    class Meta:
        model = Document
        fields = ['filename', 'file', 'document_type']
    
    def validate_file(self, value):
        """Валидация файла."""
        max_size = 50 * 1024 * 1024  # 50 MB
        if value.size > max_size:
            raise serializers.ValidationError("Размер файла превышает 50 MB")
        return value


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer для списка документов."""
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    
    class Meta:
        model = Document
        fields = [
            'id', 'filename', 'file', 'file_size', 'mime_type',
            'document_type', 'document_type_display',
            'status', 'status_display',
            'uploaded_at', 'processed_at', 'processing_time',
            'uploaded_by'
        ]
        read_only_fields = ['id', 'file_size', 'mime_type', 'file_hash']


class DocumentDetailSerializer(serializers.ModelSerializer):
    """Serializer для детальной информации о документе."""
    
    fields = DocumentFieldSerializer(many=True, read_only=True)
    tables = DocumentTableSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    
    class Meta:
        model = Document
        fields = [
            'id', 'filename', 'file', 'file_size', 'mime_type', 'file_hash',
            'document_type', 'document_type_display',
            'status', 'status_display',
            'ocr_task_id', 'extracted_data', 'raw_text',
            'processing_time', 'error_message',
            'uploaded_at', 'processed_at',
            'uploaded_by', 'fields', 'tables'
        ]
        read_only_fields = fields
