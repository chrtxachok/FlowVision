from typing import Dict, Any, List
from app.processors.base import BaseProcessor
import re


class WaybillProcessor(BaseProcessor):
    """Обработчик накладных (ТТН, накладные)."""

    def process(self, ocr_result: Dict[str, Any], image_type: str) -> Dict[str, Any]:
        """Основной метод обработки накладной."""
        full_text = ocr_result.get("full_text", "").lower()
        lines = ocr_result.get("lines", [])

        extracted_data = self._parse_waybill_fields(full_text, lines)
        confidence = self._calculate_confidence(extracted_data)

        return {
            "document_type": "waybill",
            "confidence": confidence,
            "extracted_data": extracted_data,
            "raw_text": ocr_result.get("full_text", ""),
            "metadata": {
                "fields_found": len([v for v in extracted_data.values() if v.get("value")]),
                "processing_method": self._processing_method(),
            },
        }

    @staticmethod
    def _processing_method() -> str:
        try:
            from app.config import settings
            return getattr(settings, "OCR_BACKEND", "unknown")
        except Exception:
            return "unknown"

    # ------------------------------------------------------------------
    # Парсинг полей
    # ------------------------------------------------------------------

    def _parse_waybill_fields(self, full_text: str, lines: List) -> Dict[str, Any]:
        return {
            "waybill_number": self._extract_waybill_number(full_text, lines),
            "date": self._extract_date(full_text, lines),
            "sender": self._extract_sender(full_text, lines),
            "recipient": self._extract_recipient(full_text, lines),
            "cargo_description": self._extract_cargo_description(full_text, lines),
            "cargo_mass_kg": self._extract_cargo_mass(full_text, lines),
            "total_amount": self._extract_total_amount(full_text, lines),
            "driver_name": self._extract_driver_name(full_text, lines),
            "vehicle_number": self._extract_vehicle_number(full_text, lines),
        }

    def _extract_waybill_number(self, text: str, lines: List) -> Dict:
        patterns = [
            r'накладная\s*№?\s*([а-я0-9/-]+)',
            r'ттн\s*№?\s*([а-я0-9/-]+)',
            r'№\s*([а-я0-9/-]+)\s*(?:от|дата)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return {"value": match.group(1).strip(), "confidence": 0.9, "raw_text": match.group(0)}
        return {"value": None, "confidence": 0.0}

    def _extract_date(self, text: str, lines: List) -> Dict:
        patterns = [
            r'дата[:\s]+(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})',
            r'от[:\s]+(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})',
            r'(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})\s+г\.?',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return {"value": match.group(1).strip(), "confidence": 0.85, "raw_text": match.group(0)}
        return {"value": None, "confidence": 0.0}

    def _extract_sender(self, text: str, lines: List) -> Dict:
        match = re.search(r'отправитель[:\s]+([а-яё0-9\s,.-]+?)(?:получатель|груз|итого|$)', text)
        if match:
            sender = re.sub(r'[\s,.-]+$', '', match.group(1).strip())
            return {"value": sender, "confidence": 0.8, "raw_text": match.group(0)}
        return {"value": None, "confidence": 0.0}

    def _extract_recipient(self, text: str, lines: List) -> Dict:
        match = re.search(r'получатель[:\s]+([а-яё0-9\s,.-]+?)(?:груз|итого|сумма|$)', text)
        if match:
            recipient = re.sub(r'[\s,.-]+$', '', match.group(1).strip())
            return {"value": recipient, "confidence": 0.8, "raw_text": match.group(0)}
        return {"value": None, "confidence": 0.0}

    def _extract_cargo_description(self, text: str, lines: List) -> Dict:
        match = re.search(r'груз[:\s]+([а-яё0-9\s,.-]+?)(?:масса|вес|колич|сумма|$)', text)
        if match:
            return {"value": match.group(1).strip(), "confidence": 0.75, "raw_text": match.group(0)}
        return {"value": None, "confidence": 0.0}

    def _extract_cargo_mass(self, text: str, lines: List) -> Dict:
        patterns = [
            r'масса[:\s]+(\d+(?:[.,]\d+)?)\s*(?:кг|килограм)',
            r'вес[:\s]+(\d+(?:[.,]\d+)?)\s*(?:кг|килограм)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return {"value": match.group(1).replace(',', '.'), "confidence": 0.9, "raw_text": match.group(0)}
        return {"value": None, "confidence": 0.0}

    def _extract_total_amount(self, text: str, lines: List) -> Dict:
        patterns = [
            r'итого[:\s]+(\d+(?:\s\d{3})*(?:[.,]\d{2})?)',
            r'всего\s+к\s+оплате[:\s]+(\d+(?:\s\d{3})*(?:[.,]\d{2})?)',
            r'сумма[:\s]+(\d+(?:\s\d{3})*(?:[.,]\d{2})?)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                amount = match.group(1).replace(' ', '').replace(',', '.')
                return {"value": amount, "confidence": 0.9, "raw_text": match.group(0)}
        return {"value": None, "confidence": 0.0}

    def _extract_driver_name(self, text: str, lines: List) -> Dict:
        match = re.search(r'водитель[:\s]+([а-яё\s]+?)(?:подпись|м\.п\.|табель|$)', text)
        if match:
            return {"value": match.group(1).strip(), "confidence": 0.7, "raw_text": match.group(0)}
        return {"value": None, "confidence": 0.0}

    def _extract_vehicle_number(self, text: str, lines: List) -> Dict:
        match = re.search(r'\b([а-я]{1}\d{3}[а-я]{2}\d{2,3})\b', text)
        if match:
            return {"value": match.group(1).upper(), "confidence": 0.85, "raw_text": match.group(0)}
        return {"value": None, "confidence": 0.0}