"""
Базовые Pydantic схемы для транспортной OCR системы.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from ..enums import (
    ConfidenceLevel,
    DocumentType,
    FieldType,
    ProcessingStatus,
)


class DocumentMetadata(BaseModel):
    """Метаданные документа."""
    document_id: str
    filename: str
    file_size: int
    mime_type: str
    file_hash: str
    upload_time: datetime = Field(default_factory=datetime.utcnow)
    document_type: Optional[DocumentType] = None


class FieldConfidence(BaseModel):
    """Достоверность распознавания поля."""
    confidence: float = Field(ge=0.0, le=1.0)
    level: ConfidenceLevel


class DocumentField(BaseModel):
    """Поле документа с метаданными распознавания."""
    name: str
    value: Any
    field_type: FieldType
    confidence: FieldConfidence
    page_number: Optional[int] = None
    bounding_box: Optional[Dict[str, float]] = None


class TableCell(BaseModel):
    """Ячейка таблицы."""
    row: int
    col: int
    text: str
    confidence: float
    bounding_box: Optional[Dict[str, float]] = None


class TableRow(BaseModel):
    """Строка таблицы."""
    cells: List[TableCell]


class DocumentTable(BaseModel):
    """Таблица в документе."""
    table_id: str
    rows: List[TableRow]
    headers: Optional[List[str]] = None
    page_number: int


class ExtractedData(BaseModel):
    """Извлеченные данные из документа."""
    fields: List[DocumentField] = []
    tables: List[DocumentTable] = []
    raw_text: Optional[str] = None
    normalized_text: Optional[str] = None


class ProcessingResult(BaseModel):
    """Результат обработки документа."""
    document_id: str
    status: ProcessingStatus
    extracted_data: Optional[ExtractedData] = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    completed_at: Optional[datetime] = None


class OCRRequest(BaseModel):
    """Запрос на OCR обработку."""
    file_url: str
    document_type: Optional[DocumentType] = None
    language: str = "ru"
    extract_tables: bool = True
    enhance_image: bool = True


class OCRResponse(BaseModel):
    """Ответ OCR сервиса."""
    task_id: str
    status: ProcessingStatus
    result: Optional[ProcessingResult] = None
    message: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Ответ проверки здоровья сервиса."""
    status: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    services: Optional[Dict[str, str]] = None
