"""
Извлечение полей документа с использованием LayoutLM.
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import structlog
import torch
from transformers import LayoutLMv3ForTokenClassification, LayoutLMv3Tokenizer

logger = structlog.get_logger()


class LayoutLMExtractor:
    """
    Извлечение структурированных полей из документа с помощью LayoutLM.
    
    Использует LayoutLMv3 для:
    - Named Entity Recognition (NER)
    - Классификации элементов документа
    - Извлечения ключевых полей (адреса, даты, суммы, etc.)
    """
    
    def __init__(
        self,
        model_name: str = "microsoft/layoutlmv3-base",
        max_seq_length: int = 512,
        use_gpu: bool = False,
    ):
        """
        Инициализация экстрактора LayoutLM.
        
        Args:
            model_name: Название модели
            max_seq_length: Максимальная длина последовательности
            use_gpu: Использовать GPU
        """
        self.model_name = model_name
        self.max_seq_length = max_seq_length
        self.device = "cuda" if use_gpu and torch.cuda.is_available() else "cpu"
        
        # Загрузка модели и токенизатора
        try:
            self.tokenizer = LayoutLMv3Tokenizer.from_pretrained(model_name)
            self.model = LayoutLMv3ForTokenClassification.from_pretrained(
                model_name,
                num_labels=51  # Стандартное количество классов для документов
            )
            self.model.to(self.device)
            self.model.eval()
            
            logger.info(
                "LayoutLMExtractor initialized",
                model_name=model_name,
                device=self.device,
            )
        except Exception as e:
            logger.warning(f"Failed to load LayoutLM model: {e}. Using fallback.")
            self.model = None
            self.tokenizer = None
    
    def extract(
        self,
        image: np.ndarray,
        recognized_texts: List[Dict[str, Any]],
        text_regions: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Извлечение полей из распознанного текста.
        
        Args:
            image: Изображение документа
            recognized_texts: Список распознанных текстов
            text_regions: Список текстовых регионов
            
        Returns:
            Список извлеченных полей
        """
        if not recognized_texts:
            return []
        
        # Если модель недоступна, используем правила
        if self.model is None:
            return self._extract_by_rules(recognized_texts)
        
        try:
            return self._extract_with_model(recognized_texts, text_regions)
        except Exception as e:
            logger.error("LayoutLM extraction failed, using fallback", error=str(e))
            return self._extract_by_rules(recognized_texts)
    
    def _extract_with_model(
        self,
        recognized_texts: List[Dict[str, Any]],
        text_regions: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Извлечение с использованием модели."""
        fields = []
        
        # Подготовка данных для модели
        words = [text["text"] for text in recognized_texts]
        boxes = []
        for text in recognized_texts:
            bbox = text.get("bbox", {})
            boxes.append([
                int(bbox.get("x_min", 0)),
                int(bbox.get("y_min", 0)),
                int(bbox.get("x_max", 0)),
                int(bbox.get("y_max", 0)),
            ])
        
        # Токенизация
        encoding = self.tokenizer(
            words,
            boxes=boxes,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.max_seq_length,
        )
        
        # Перенос на устройство
        encoding = {k: v.to(self.device) for k, v in encoding.items()}
        
        # Предсказание
        with torch.no_grad():
            outputs = self.model(**encoding)
            predictions = torch.argmax(outputs.logits, dim=-1)
        
        # Преобразование предсказаний в метки
        predicted_labels = self.tokenizer.convert_ids_to_tokens(predictions[0])
        
        # Извлечение полей
        current_field = None
        current_value = []
        
        for i, (word, label) in enumerate(zip(words, predicted_labels)):
            if label.startswith("B-"):
                # Начало нового поля
                if current_field:
                    fields.append({
                        "name": current_field,
                        "value": " ".join(current_value),
                        "type": self._get_field_type(current_field),
                    })
                current_field = label[2:]
                current_value = [word]
            elif label.startswith("I-") and current_field:
                current_value.append(word)
            else:
                if current_field:
                    fields.append({
                        "name": current_field,
                        "value": " ".join(current_value),
                        "type": self._get_field_type(current_field),
                    })
                current_field = None
                current_value = []
        
        # Добавление последнего поля
        if current_field:
            fields.append({
                "name": current_field,
                "value": " ".join(current_value),
                "type": self._get_field_type(current_field),
            })
        
        return fields
    
    def _extract_by_rules(
        self,
        recognized_texts: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Извлечение полей по правилам (fallback).
        
        Использует регулярные выражения для поиска типовых полей.
        """
        from shared.utils import (
            extract_date_from_text,
            extract_inn,
            extract_vin,
            extract_license_plate,
        )
        
        fields = []
        full_text = " ".join([t["text"] for t in recognized_texts])
        
        # Поиск дат
        dates = []
        for text in recognized_texts:
            date = extract_date_from_text(text["text"])
            if date:
                dates.append({
                    "value": date.strftime("%d.%m.%Y"),
                    "confidence": text.get("confidence", 0.9),
                    "bbox": text.get("bbox"),
                })
        
        if dates:
            fields.append({
                "name": "date",
                "value": dates[0]["value"],
                "type": "date",
                "confidence": dates[0]["confidence"],
            })
        
        # Поиск ИНН
        inn = extract_inn(full_text)
        if inn:
            fields.append({
                "name": "inn",
                "value": inn,
                "type": "inn",
                "confidence": 0.9,
            })
        
        # Поиск VIN
        vin = extract_vin(full_text)
        if vin:
            fields.append({
                "name": "vin",
                "value": vin,
                "type": "vin",
                "confidence": 0.9,
            })
        
        # Поиск госномера
        license_plate = extract_license_plate(full_text)
        if license_plate:
            fields.append({
                "name": "license_plate",
                "value": license_plate,
                "type": "license_plate",
                "confidence": 0.9,
            })
        
        return fields
    
    def _get_field_type(self, field_name: str) -> str:
        """Определение типа поля по имени."""
        field_mapping = {
            "date": "date",
            "time": "time",
            "amount": "number",
            "total": "number",
            "address": "address",
            "inn": "inn",
            "kpp": "kpp",
            "phone": "phone",
            "email": "email",
            "vin": "vin",
            "license": "license_plate",
        }
        return field_mapping.get(field_name.lower(), "text")
