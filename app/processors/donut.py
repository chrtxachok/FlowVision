"""
Интеграция Donut с процессорами документов.

Пример: использование результата Donut для структурированного извлечения данных.
"""

from typing import Dict, Any, Optional
import json
import re
import logging

from app.processors.base import BaseProcessor

logger = logging.getLogger(__name__)


class DonutProcessor(BaseProcessor):
    """
    Процессор для работы с результатами Donut модели.
    
    В отличие от стандартных процессоров (WaybillProcessor и т.д.),
    которые работают с raw OCR текстом, DonutProcessor работает
    с уже структурированным JSON выводом от Donut.
    """

    def process(self, ocr_result: Dict[str, Any], image_type: str) -> Dict[str, Any]:
        """
        Обрабатывает результат Donut (JSON структуру).

        Parameters
        ----------
        ocr_result : dict
            Результат от DonutExtractor.extract(), содержит:
            - "text": str — JSON или структурированный вывод
            - "confidence": float — уверенность модели
            - "metadata": dict
        image_type : str
            MIME-тип исходного файла

        Returns
        -------
        dict с полями:
            document_type, confidence, extracted_data, raw_text, metadata
        """
        raw_text = ocr_result.get("text", "")
        
        # Парсим JSON из raw_text
        extracted_data = self._parse_json_output(raw_text)
        
        # Нормализуем данные по типам документов
        normalized_data = self._normalize_fields(extracted_data)
        
        # Вычисляем уверенность
        confidence = ocr_result.get("confidence", 0.95)
        
        return {
            "document_type": "donut_extracted",
            "confidence": confidence,
            "extracted_data": normalized_data,
            "raw_text": raw_text,
            "metadata": {
                "fields_found": len([v for v in normalized_data.values() if v.get("value")]),
                "processing_method": "donut",
                "parser_version": "1.0",
                **ocr_result.get("metadata", {}),
            },
        }

    @staticmethod
    def _parse_json_output(raw_text: str) -> Dict[str, Any]:
        """Парсит JSON из raw Donut output."""
        try:
            # Ищем JSON в raw text
            start_idx = raw_text.find('{')
            end_idx = raw_text.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_str = raw_text[start_idx:end_idx + 1]
                data = json.loads(json_str)
                logger.debug(f"JSON успешно распарсен из Donut output")
                return data
            
            logger.warning("JSON не найден в Donut output")
            return {"raw_text": raw_text}
        
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка при парсинге JSON: {e}")
            return {"raw_text": raw_text, "parse_error": str(e)}

    @staticmethod
    def _normalize_fields(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Нормализует поля из Donut в стандартный формат.
        
        Стандартный формат:
        {
            "field_name": {
                "value": str | None,
                "confidence": float,
                "bbox": [x1, y1, x2, y2] | None,
                "raw_text": str | None,
            }
        }
        """
        normalized = {}
        
        for key, value in data.items():
            if value is None:
                normalized[key] = {
                    "value": None,
                    "confidence": 0.0,
                    "raw_text": None,
                }
            elif isinstance(value, dict):
                # Если это уже структурированное поле
                normalized[key] = {
                    "value": value.get("value") or str(value),
                    "confidence": value.get("confidence", 0.95),
                    "raw_text": value.get("raw_text"),
                }
            elif isinstance(value, (list, dict)):
                # Сложные типы (таблицы, вложенные структуры)
                normalized[key] = {
                    "value": json.dumps(value),  # Сохраняем как JSON
                    "confidence": 0.95,
                    "raw_text": json.dumps(value),
                }
            else:
                # Простые значения
                normalized[key] = {
                    "value": str(value),
                    "confidence": 0.95,
                    "raw_text": str(value),
                }
        
        return normalized


# ------------------------------------------------------------------
# Примеры использования
# ------------------------------------------------------------------

def example_usage():
    """Пример использования DonutProcessor."""
    
    # Результат от DonutExtractor
    donut_result = {
        "text": json.dumps({
            "invoice_number": "INV-2024-001",
            "date": "2024-05-14",
            "seller": "ООО \"Компания А\"",
            "buyer": "ПАО \"Компания Б\"",
            "total": 15000.00,
            "items": [
                {"name": "Товар 1", "quantity": 10, "price": 1000},
                {"name": "Товар 2", "quantity": 5, "price": 1000},
            ]
        }),
        "confidence": 0.97,
        "metadata": {"model": "donut-base"}
    }
    
    # Создаем процессор
    processor = DonutProcessor()
    
    # Обрабатываем результат
    result = processor.process(donut_result, image_type="image/jpeg")
    
    print("Результат обработки:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Выходные данные:
    # {
    #   "document_type": "donut_extracted",
    #   "confidence": 0.97,
    #   "extracted_data": {
    #     "invoice_number": {
    #       "value": "INV-2024-001",
    #       "confidence": 0.95,
    #       "raw_text": "INV-2024-001"
    #     },
    #     ...
    #   }
    # }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    example_usage()
