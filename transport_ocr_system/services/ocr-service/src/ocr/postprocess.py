"""
Постобработка распознанного текста.
"""

import logging
import re
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()


class TextPostprocessor:
    """
    Постобработчик текста для улучшения качества распознавания.
    
    Операции:
    - Исправление пробелов
    - Исправление переносов
    - Нормализация пробелов
    - Форматирование специальных полей
    """
    
    def __init__(
        self,
        fix_spacing: bool = True,
        fix_hyphenation: bool = True,
        normalize_whitespace: bool = True,
    ):
        """
        Инициализация постобработчика.
        
        Args:
            fix_spacing: Исправлять пробелы
            fix_hyphenation: Исправлять переносы
            normalize_whitespace: Нормализовать пробелы
        """
        self.fix_spacing = fix_spacing
        self.fix_hyphenation = fix_hyphenation
        self.normalize_whitespace = normalize_whitespace
        
        logger.info("TextPostprocessor initialized")
    
    def process(
        self,
        extracted_fields: List[Dict[str, Any]],
        recognized_texts: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Постобработка извлеченных данных.
        
        Args:
            extracted_fields: Извлеченные поля
            recognized_texts: Распознанные тексты
            
        Returns:
            Обработанные поля
        """
        processed_fields = []
        
        for field in extracted_fields:
            processed_field = self._process_field(field)
            processed_fields.append(processed_field)
        
        # Дополнительная обработка распознанных текстов
        processed_texts = []
        for text in recognized_texts:
            processed_text = self._process_text(text)
            processed_texts.append(processed_text)
        
        return processed_fields
    
    def _process_field(self, field: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка отдельного поля."""
        processed = field.copy()
        
        if "value" in processed and isinstance(processed["value"], str):
            value = processed["value"]
            
            # Исправление переносов
            if self.fix_hyphenation:
                value = self._fix_hyphenation(value)
            
            # Исправление пробелов
            if self.fix_spacing:
                value = self._fix_spacing(value)
            
            # Нормализация пробелов
            if self.normalize_whitespace:
                value = self._normalize_whitespace(value)
            
            # Форматирование в зависимости от типа
            field_type = processed.get("type", "text")
            value = self._format_by_type(value, field_type)
            
            processed["value"] = value
        
        return processed
    
    def _process_text(self, text: Dict[str, Any]) -> Dict[str, Any]:
        """Обработка распознанного текста."""
        processed = text.copy()
        
        if "text" in processed:
            text_value = processed["text"]
            
            if self.fix_hyphenation:
                text_value = self._fix_hyphenation(text_value)
            
            if self.fix_spacing:
                text_value = self._fix_spacing(text_value)
            
            if self.normalize_whitespace:
                text_value = self._normalize_whitespace(text_value)
            
            processed["text"] = text_value
        
        return processed
    
    def _fix_hyphenation(self, text: str) -> str:
        """Исправление переносов слов."""
        # Удаление переноса в конце строки
        text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', text)
        return text
    
    def _fix_spacing(self, text: str) -> str:
        """Исправление проблем с пробелами."""
        # Пробел перед знаками препинания
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)
        
        # Пробел после знаков препинания
        text = re.sub(r'([.,;:!?])([А-Яа-яA-Za-z])', r'\1 \2', text)
        
        # Множественные пробелы
        text = re.sub(r' {2,}', ' ', text)
        
        return text.strip()
    
    def _normalize_whitespace(self, text: str) -> str:
        """Нормализация пробельных символов."""
        # Замена всех пробельных символов на один пробел
        text = re.sub(r'\s+', ' ', text)
        
        # Удаление пробелов в начале и конце строки
        text = text.strip()
        
        return text
    
    def _format_by_type(self, value: str, field_type: str) -> str:
        """Форматирование значения в зависимости от типа поля."""
        formatters = {
            "date": self._format_date,
            "inn": self._format_inn,
            "phone": self._format_phone,
            "email": self._format_email,
            "number": self._format_number,
            "address": self._format_address,
        }
        
        formatter = formatters.get(field_type)
        if formatter:
            return formatter(value)
        
        return value
    
    def _format_date(self, value: str) -> str:
        """Форматирование даты."""
        # Приводим к формату ДД.ММ.ГГГГ
        date_patterns = [
            (r'(\d{4})-(\d{2})-(\d{2})', r'\3.\2.\1'),  # ГГГГ-ММ-ДД -> ДД.ММ.ГГГГ
            (r'(\d{2})/(\d{2})/(\d{4})', r'\1.\2.\3'),  # ДД/ММ/ГГГГ -> ДД.ММ.ГГГГ
        ]
        
        for pattern, replacement in date_patterns:
            value = re.sub(pattern, replacement, value)
        
        return value
    
    def _format_inn(self, value: str) -> str:
        """Форматирование ИНН."""
        # Оставляем только цифры
        digits = re.sub(r'\D', '', value)
        
        # Форматируем: 10 цифр - ИНН ЮЛ, 12 цифр - ИНН ФЛ
        if len(digits) == 10:
            return f"{digits[:4]} {digits[4:]} {digits[6:]}"
        elif len(digits) == 12:
            return f"{digits[:4]} {digits[4:]} {digits[6:10]} {digits[10:]}"
        
        return value
    
    def _format_phone(self, value: str) -> str:
        """Форматирование телефона."""
        # Оставляем только цифры
        digits = re.sub(r'\D', '', value)
        
        if len(digits) == 11 and digits[0] == '7':
            digits = digits[1:]
        
        if len(digits) == 10:
            return f"+7 ({digits[:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:10]}"
        
        return value
    
    def _format_email(self, value: str) -> str:
        """Форматирование email."""
        return value.lower().strip()
    
    def _format_number(self, value: str) -> str:
        """Форматирование чисел."""
        # Удаляем пробелы между разрядами
        value = value.replace(' ', '')
        
        # Добавляем пробелы между разрядами для больших чисел
        if re.match(r'^\d+$', value):
            return '{:,}'.format(int(value)).replace(',', ' ')
        
        return value
    
    def _format_address(self, value: str) -> str:
        """Форматирование адреса."""
        # Стандартизация названий
        replacements = {
            r'\bг\.\s*': 'г. ',
            r'\bобл\.\s*': 'обл. ',
            r'\bр-н\b': 'р-н',
            r'\bул\.\s*': 'ул. ',
            r'\bд\.\s*': 'д. ',
            r'\bкорп\.\s*': 'корп. ',
            r'\bстр\.\s*': 'стр. ',
        }
        
        for pattern, replacement in replacements.items():
            value = re.sub(pattern, replacement, value, flags=re.IGNORECASE)
        
        return value
