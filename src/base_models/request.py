from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class DocumentType(str, Enum):
    WAYBILL = "waybill"
    INVOICE = "invoice"
    ACT = "act"
    UPD = "upd"
    CUSTOM = "custom"

class OCRRequest(BaseModel):
    """Запрос на обработку документа"""
    document_type: DocumentType = Field(
        default=DocumentType.WAYBILL,
        description="Тип документа для обработки"
    )
    enhance_image: bool = Field(
        default=True,
        description="Улучшать качество изображения перед обработкой"
    )
    extract_tables: bool = Field(
        default=True,
        description="Извлекать таблицы из документа"
    )
    return_raw_text: bool = Field(
        default=False,
        description="Возвращать необработанный текст"
    )