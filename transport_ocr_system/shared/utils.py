"""
Общие утилиты для транспортной OCR системы.
"""

import hashlib
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from .enums import ConfidenceLevel


def generate_document_id() -> str:
    """Генерация уникального ID для документа."""
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    return f"doc_{timestamp}"


def calculate_file_hash(file_content: bytes) -> str:
    """Вычисление хеша файла."""
    return hashlib.sha256(file_content).hexdigest()


def sanitize_filename(filename: str) -> str:
    """Санитизация имени файла."""
    # Удаляем небезопасные символы
    sanitized = re.sub(r'[^\w\s.-]', '', filename)
    # Заменяем пробелы на подчеркивания
    sanitized = re.sub(r'\s+', '_', sanitized)
    return sanitized


def parse_date_from_text(text: str) -> Optional[datetime]:
    """Извлечение даты из текста."""
    date_patterns = [
        r'\d{2}\.\d{2}\.\d{4}',
        r'\d{2}/\d{2}/\d{4}',
        r'\d{4}-\d{2}-\d{2}',
        r'\d{2}-\d{2}-\d{4}',
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            date_str = match.group()
            for fmt in ['%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
    return None


def extract_inn(text: str) -> Optional[str]:
    """Извлечение ИНН из текста."""
    # ИНН юридического лица - 10 цифр, ИНН физического лица - 12 цифр
    inn_pattern = r'\b\d{10}\b|\b\d{12}\b'
    match = re.search(inn_pattern, text)
    return match.group() if match else None


def extract_vin(text: str) -> Optional[str]:
    """Извлечение VIN номера из текста."""
    # VIN состоит из 17 символов (латинские буквы и цифры, кроме I, O, Q)
    vin_pattern = r'\b[A-HJ-NPR-Z0-9]{17}\b'
    match = re.search(vin_pattern, text)
    return match.group().upper() if match else None


def extract_license_plate(text: str) -> Optional[str]:
    """Извлечение государственного номера ТС."""
    # Российские номера: А777АА77 или А777АА777
    plate_pattern = r'\b[АВЕКМНОРСТУХ]\d{3}[АВЕКМНОРСТУХ]{2}\d{2,3}\b'
    match = re.search(plate_pattern, text)
    return match.group().upper() if match else None


def get_confidence_level(confidence: float) -> ConfidenceLevel:
    """Определение уровня достоверности."""
    if confidence >= 0.9:
        return ConfidenceLevel.HIGH
    elif confidence >= 0.7:
        return ConfidenceLevel.MEDIUM
    else:
        return ConfidenceLevel.LOW


def format_confidence(confidence: float) -> str:
    """Форматирование достоверности в проценты."""
    return f"{confidence * 100:.1f}%"


def merge_dict_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """Объединение значений словаря."""
    result = {}
    for key, value in data.items():
        if isinstance(value, list):
            result[key] = value
        elif isinstance(value, dict):
            result[key] = merge_dict_values(value)
        else:
            result[key] = value
    return result


def validate_required_fields(
    data: Dict[str, Any], 
    required_fields: List[str]
) -> List[str]:
    """Валидация обязательных полей.
    
    Returns:
        Список отсутствующих полей.
    """
    missing = []
    for field in required_fields:
        if field not in data or data[field] is None:
            missing.append(field)
    return missing


def truncate_text(text: str, max_length: int = 100) -> str:
    """Обрезание текста до максимальной длины."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."
