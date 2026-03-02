"""
Базовый класс для всех процессоров документов.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseProcessor(ABC):
    """Абстрактный процессор документа."""

    @abstractmethod
    def process(self, ocr_result: Dict[str, Any], image_type: str) -> Dict[str, Any]:
        """
        Обрабатывает результат OCR и возвращает структурированные данные.

        Parameters
        ----------
        ocr_result : dict
            Словарь из `postprocess.parse_ocr_result()`:
            {"full_text": str, "lines": list, "blocks": list}
        image_type : str
            MIME-тип исходного файла (например, "image/jpeg").

        Returns
        -------
        dict с полями:
            document_type, confidence, extracted_data, raw_text, metadata
        """
        ...

    def _calculate_confidence(self, extracted_data: Dict[str, Any]) -> float:
        """Усредняет confidence по всем найденным полям."""
        confidences = [
            field.get("confidence", 0.0)
            for field in extracted_data.values()
            if isinstance(field, dict)
        ]
        if not confidences:
            return 0.0
        return round(sum(confidences) / len(confidences), 4)
