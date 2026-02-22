from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

class ProcessingStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"

class FieldValue(BaseModel):
    """Значение поля с метаданными"""
    value: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    bbox: Optional[List[int]] = None  # [x1, y1, x2, y2]
    raw_text: Optional[str] = None

class WaybillData(BaseModel):
    """Структурированные данные накладной"""
    waybill_number: FieldValue = Field(default_factory=FieldValue)
    date: FieldValue = Field(default_factory=FieldValue)
    sender: FieldValue = Field(default_factory=FieldValue)
    recipient: FieldValue = Field(default_factory=FieldValue)
    cargo_description: FieldValue = Field(default_factory=FieldValue)
    cargo_mass_kg: FieldValue = Field(default_factory=FieldValue)
    total_amount: FieldValue = Field(default_factory=FieldValue)
    driver_name: FieldValue = Field(default_factory=FieldValue)
    vehicle_number: FieldValue = Field(default_factory=FieldValue)

class InvoiceData(BaseModel):
    """Структурированные данные счёта"""
    invoice_number: FieldValue = Field(default_factory=FieldValue)
    date: FieldValue = Field(default_factory=FieldValue)
    seller: FieldValue = Field(default_factory=FieldValue)
    buyer: FieldValue = Field(default_factory=FieldValue)
    items: List[Dict[str, Any]] = Field(default_factory=list)
    total: FieldValue = Field(default_factory=FieldValue)

class OCRResponse(BaseModel):
    """Ответ сервиса распознавания"""
    status: ProcessingStatus
    document_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    processing_time_ms: int
    extracted_data: Dict[str, Any]
    raw_text: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ErrorResponse(BaseModel):
    """Ответ об ошибке"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None