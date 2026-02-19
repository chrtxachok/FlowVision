"""Admin configuration for documents app."""

from django.contrib import admin
from .models import Document, DocumentField, DocumentTable


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Admin interface for Document model."""
    list_display = ['filename', 'document_type', 'status', 'uploaded_at', 'processed_at']
    list_filter = ['status', 'document_type', 'uploaded_at']
    search_fields = ['filename', 'file_hash']
    readonly_fields = ['id', 'file_hash', 'uploaded_at', 'processed_at']
    fieldsets = [
        ('Основная информация', {
            'fields': ['id', 'filename', 'file', 'file_size', 'mime_type', 'file_hash']
        }),
        ('Тип и статус', {
            'fields': ['document_type', 'status', 'uploaded_by']
        }),
        ('OCR результаты', {
            'fields': ['ocr_task_id', 'extracted_data', 'raw_text', 'processing_time', 'error_message']
        }),
        ('Временные метки', {
            'fields': ['uploaded_at', 'processed_at']
        }),
    ]


@admin.register(DocumentField)
class DocumentFieldAdmin(admin.ModelAdmin):
    """Admin interface for DocumentField model."""
    list_display = ['name', 'value', 'field_type', 'confidence', 'document']
    list_filter = ['field_type']
    search_fields = ['name', 'value']


@admin.register(DocumentTable)
class DocumentTableAdmin(admin.ModelAdmin):
    """Admin interface for DocumentTable model."""
    list_display = ['table_id', 'page_number', 'document']
    list_filter = ['page_number']
