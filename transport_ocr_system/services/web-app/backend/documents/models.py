"""Models for documents app."""

import hashlib
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class DocumentType(models.TextChoices):
    """Типы поддерживаемых документов."""
    TRANSPORT_WAYBILL = 'transport_waybill', 'Транспортная накладная'
    BILL_OF_LADING = 'bill_of_lading', 'Коносамент'
    INVOICE = 'invoice', 'Счет-фактура'
    PACKING_LIST = 'packing_list', 'Упаковочный лист'
    CUSTOM_DECLARATION = 'custom_declaration', 'Таможенная декларация'
    DRIVER_LICENSE = 'driver_license', 'Водительское удостоверение'
    VEHICLE_REGISTRATION = 'vehicle_registration', 'Регистрация ТС'
    UNKNOWN = 'unknown', 'Неизвестный'


class ProcessingStatus(models.TextChoices):
    """Статусы обработки документов."""
    PENDING = 'pending', 'Ожидает обработки'
    QUEUED = 'queued', 'В очереди'
    PROCESSING = 'processing', 'В процессе'
    COMPLETED = 'completed', 'Успешно обработан'
    FAILED = 'failed', 'Ошибка'
    PARTIAL_SUCCESS = 'partial_success', 'Частично обработан'


class Document(models.Model):
    """Модель документа."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    filename = models.CharField(max_length=255, verbose_name='Имя файла')
    file = models.FileField(upload_to='documents/%Y/%m/%d/', verbose_name='Файл')
    file_size = models.IntegerField(verbose_name='Размер файла')
    mime_type = models.CharField(max_length=100, verbose_name='MIME тип')
    file_hash = models.CharField(max_length=64, verbose_name='Хеш файла')
    
    # Тип документа
    document_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices,
        default=DocumentType.UNKNOWN,
        verbose_name='Тип документа'
    )
    
    # Статус обработки
    status = models.CharField(
        max_length=30,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
        verbose_name='Статус обработки'
    )
    
    # Результат OCR
    ocr_task_id = models.CharField(max_length=100, blank=True, verbose_name='ID OCR задачи')
    extracted_data = models.JSONField(blank=True, null=True, verbose_name='Извлеченные данные')
    raw_text = models.TextField(blank=True, verbose_name='Распознанный текст')
    processing_time = models.FloatField(blank=True, null=True, verbose_name='Время обработки')
    error_message = models.TextField(blank=True, verbose_name='Сообщение об ошибке')
    
    # Временные метки
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата загрузки')
    processed_at = models.DateTimeField(blank=True, null=True, verbose_name='Дата обработки')
    
    # Пользователь
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents',
        verbose_name='Загрузил'
    )
    
    class Meta:
        db_table = 'documents'
        verbose_name = 'Документ'
        verbose_name_plural = 'Документы'
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['-uploaded_at']),
            models.Index(fields=['status']),
            models.Index(fields=['document_type']),
        ]
    
    def __str__(self):
        return f'{self.filename} ({self.get_status_display()})'
    
    def calculate_hash(self):
        """Вычисление хеша файла."""
        if self.file:
            self.file_hash = hashlib.sha256(self.file.read()).hexdigest()
            self.file.seek(0)
    
    def save(self, *args, **kwargs):
        if not self.file_hash and self.file:
            self.calculate_hash()
        super().save(*args, **kwargs)


class DocumentField(models.Model):
    """Извлеченное поле из документа."""
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='fields',
        verbose_name='Документ'
    )
    name = models.CharField(max_length=100, verbose_name='Имя поля')
    value = models.TextField(verbose_name='Значение')
    field_type = models.CharField(max_length=50, verbose_name='Тип поля')
    confidence = models.FloatField(verbose_name='Достоверность')
    page_number = models.IntegerField(blank=True, null=True, verbose_name='Номер страницы')
    
    class Meta:
        db_table = 'document_fields'
        verbose_name = 'Поле документа'
        verbose_name_plural = 'Поля документа'
    
    def __str__(self):
        return f'{self.name}: {self.value[:50]}...'


class DocumentTable(models.Model):
    """Таблица в документе."""
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='tables',
        verbose_name='Документ'
    )
    table_id = models.CharField(max_length=100, verbose_name='ID таблицы')
    page_number = models.IntegerField(verbose_name='Номер страницы')
    headers = models.JSONField(blank=True, null=True, verbose_name='Заголовки')
    data = models.JSONField(verbose_name='Данные таблицы')
    
    class Meta:
        db_table = 'document_tables'
        verbose_name = 'Таблица документа'
        verbose_name_plural = 'Таблицы документа'
    
    def __str__(self):
        return f'Таблица {self.table_id} ({self.document.filename})'
