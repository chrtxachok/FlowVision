from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class DocumentType(str, Enum):
    WAYBILL = "waybill"
    INVOICE = "invoice"
    ACT = "act"
    OTHER = "other"


class ProcessDocumentRequest(BaseModel):
    """Request schema for document processing"""
    document_id: str = Field(..., description="External document identifier")
    file_path: str = Field(..., description="Path to file in storage")
    document_type: DocumentType = Field(default=DocumentType.WAYBILL)
    
    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "file_path": "documents/user_123/abc123.jpg",
                "document_type": "waybill"
            }
        }


class ProcessDocumentResponse(BaseModel):
    """Response schema for document processing"""
    task_id: str
    status: str
    message: str
    document_id: str
    result: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_123",
                "status": "processing",
                "message": "Document processing started",
                "document_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }


class TaskStatusResponse(BaseModel):
    """Response schema for task status"""
    task_id: str
    status: str
    progress: int = Field(ge=0, le=100)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task_123",
                "status": "completed",
                "progress": 100,
                "result": {
                    "extracted_data": {...},
                    "confidence": 0.95
                }
            }
        }


class ErrorResponse(BaseModel):
    """Error response schema"""
    detail: str
    error: Optional[str] = None