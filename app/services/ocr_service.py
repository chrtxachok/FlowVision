"""
OCR-сервис — EasyOCR/PaddleOCR или Donut (end-to-end).
"""
import asyncio
import logging
import time
from typing import Any, Dict, Optional

from app.base_models.response import OCRResponse, ProcessingStatus
from app.ocr.pipeline import OCRPipeline
from app.ocr.postprocess import parse_ocr_result
from app.ocr.preprocess import bytes_to_numpy, enhance_image

logger = logging.getLogger(__name__)


class OCRService:
    """Точка входа для обработки документов."""

    def __init__(self):
        from app.config import settings

        self._backend = (settings.OCR_BACKEND or "easyocr").lower().strip()
        logger.info("Инициализация OCRService (backend=%s)...", self._backend)

        self._pipeline: Optional[OCRPipeline] = None
        self._donut = None
        self._processors: Dict[str, Any] = {}

        if self._backend == "donut":
            from app.ocr.donut_inference import DonutInference

            self._donut = DonutInference.from_settings()
        else:
            self._pipeline = OCRPipeline.from_settings()
            self._processors = self._load_processors()

        logger.info("OCRService готов (backend=%s)", self._backend)

    @staticmethod
    def _load_processors() -> Dict[str, Any]:
        from app.processors.waybill import WaybillProcessor

        return {"waybill": WaybillProcessor()}

    async def process_document(
        self, file_bytes: bytes, file_type: str, document_type: str
    ) -> OCRResponse:
        start_ms = time.time()

        if self._backend == "donut":
            extracted_data, raw_text, confidence, warnings = await asyncio.get_event_loop().run_in_executor(
                None, self._run_donut, file_bytes, file_type, document_type
            )
            lines_detected = 0
        else:
            ocr_result = await asyncio.get_event_loop().run_in_executor(
                None, self._run_ocr, file_bytes, file_type
            )
            processor = self._processors.get(document_type)
            if processor is None:
                logger.warning("Нет процессора для типа '%s'", document_type)
                extracted_data = {}
                confidence = 0.0
                warnings = [f"Unknown document_type '{document_type}', raw OCR only"]
            else:
                result = processor.process(ocr_result, file_type)
                extracted_data = result.get("extracted_data", {})
                confidence = result.get("confidence", 0.0)
                warnings = []
            raw_text = ocr_result.get("full_text", "")
            lines_detected = len(ocr_result.get("lines", []))

        elapsed_ms = int((time.time() - start_ms) * 1000)

        return OCRResponse(
            status=ProcessingStatus.SUCCESS if extracted_data else ProcessingStatus.PARTIAL,
            document_type=document_type,
            confidence=confidence,
            processing_time_ms=elapsed_ms,
            extracted_data=extracted_data,
            raw_text=raw_text,
            warnings=warnings,
            metadata={
                "lines_detected": lines_detected,
                "file_type": file_type,
                "ocr_backend": self._backend,
            },
        )

    def _run_donut(self, file_bytes: bytes, file_type: str, document_type: str):
        from app.ocr.donut_inference import DonutInference

        assert self._donut is not None

        if file_type == "application/pdf":
            img = bytes_to_numpy(file_bytes, file_type)
            gt_parse, sequence = self._donut.predict_numpy(img)
        else:
            gt_parse, sequence = self._donut.predict_bytes(file_bytes)

        extracted_data = DonutInference.to_extracted_data(gt_parse)
        confidence = DonutInference.average_confidence(extracted_data)
        warnings = [] if document_type == "waybill" else [f"Donut tuned for waybill, got '{document_type}'"]
        return extracted_data, sequence, confidence, warnings

    def _run_ocr(self, file_bytes: bytes, file_type: str) -> Dict[str, Any]:
        assert self._pipeline is not None
        img = bytes_to_numpy(file_bytes, file_type)
        img = enhance_image(img)
        raw = self._pipeline.run(img)
        return parse_ocr_result(raw)
