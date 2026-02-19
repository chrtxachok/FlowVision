"""
Pydantic схемы для API OCR сервиса.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from shared.enums import (
    ConfidenceLevel,
    DocumentType,
    FieldType,
    ProcessingStatus,
)


class FieldConfidenceSchema(BaseModel):
    """Достоверность распознавания поля."""
    confidence: float = Field(ge=0.0, le=1.0)
    level: ConfidenceLevel


class DocumentFieldSchema(BaseModel):
    """Поле документа."""
    name: str
    value: Any
    field_type: FieldType
    confidence: FieldConfidenceSchema
    page_number: Optional[int] = None
    bounding_box: Optional[Dict[str, float]] = None


class TableCellSchema(BaseModel):
    """Ячейка таблицы."""
    row: int
    col: int
    text: str
    confidence: float
    bounding_box: Optional[Dict[str, float]] = None


class TableRowSchema(BaseModel):
    """Строка таблицы."""
    cells: List[TableCellSchema]


class DocumentTableSchema(BaseModel):
    """Таблица в документе."""
    table_id: str
    rows: List[TableRowSchema]
    headers: Optional[List[str]] = None
    page_number: int


class ExtractedDataSchema(BaseModel):
    """Извлеченные данные."""
    fields: List[DocumentFieldSchema] = []
    tables: List[DocumentTableSchema] = []
    raw_text: Optional[str] = None
    normalized_text: Optional[str] = None


class ProcessingResultSchema(BaseModel):
    """Результат обработки."""
    document_id: str
    status: ProcessingStatus
    extracted_data: Optional[ExtractedDataSchema] = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    completed_at: Optional[datetime] = None


class OCRTaskRequest(BaseModel):
    """Запрос на создание OCR задачи."""
    file_url: str = Field(..., description="URL файла в MinIO")
    document_type: Optional[DocumentType] = Field(
        default=None, 
        description="Тип документа (опционально)"
    )
    language: str = Field(default="ru", description="Язык документа")
    extract_tables: bool = Field(
        default=True, 
        description="Извлекать таблицы"
    )
    enhance_image: bool = Field(
        default=True, 
        description="Улучшать качество изображения"
    )
    callback_url: Optional[str] = Field(
        default=None,
        description="URL для уведомления о завершении"
    )


class OCRTaskResponse(BaseModel):
    """Ответ на создание OCR задачи."""
    task_id: str
    status: ProcessingStatus
    message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OCRTaskStatusResponse(BaseModel):
    """Статус OCR задачи."""
    task_id: str
    status: ProcessingStatus
    result: Optional[ProcessingResultSchema] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class HealthCheckResponse(BaseModel):
    """Проверка здоровья сервиса."""
    status: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: Optional[Dict[str, str]] = None
