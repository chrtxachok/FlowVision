"""
OCR-сервис — обёртка над OCRPipeline и процессорами документов.
Инициализируется один раз при старте FastAPI (lifespan).
"""
import asyncio
import logging
import time
from typing import Any, Dict

from app.ocr.pipeline import OCRPipeline
from app.ocr.preprocess import bytes_to_numpy, enhance_image
from app.ocr.postprocess import parse_ocr_result
from app.base_models.response import OCRResponse, ProcessingStatus

logger = logging.getLogger(__name__)


class OCRService:
    """
    Точка входа для обработки документов.

    Использование
    -------------
    В lifespan FastAPI:
        service = OCRService()
        app.state.ocr_service = service

    В эндпоинте:
        result = await service.process_document(file_bytes, file_type, doc_type)
    """

    def __init__(self):
        logger.info("Инициализация OCRService...")
        self._pipeline = OCRPipeline.from_settings()
        self._processors = self._load_processors()
        logger.info("OCRService готов к работе (backend=%s)", getattr(self._pipeline, "backend", "unknown"))

    # ------------------------------------------------------------------
    # Загрузка процессоров
    # ------------------------------------------------------------------

    @staticmethod
    def _load_processors() -> Dict[str, Any]:
        """Возвращает словарь процессоров по типу документа."""
        from app.processors.waybill import WaybillProcessor
        # Добавьте сюда другие процессоры по мере их реализации:
        # from app.processors.invoice import InvoiceProcessor
        return {
            "waybill": WaybillProcessor(),
            # "invoice": InvoiceProcessor(),
            # "act": ActProcessor(),
            # "upd": UpdProcessor(),
        }

    # ------------------------------------------------------------------
    # Основной метод
    # ------------------------------------------------------------------

    async def process_document(
        self, file_bytes: bytes, file_type: str, document_type: str
    ) -> OCRResponse:
        """
        Извлекает текст и структурированные данные из документа.

        Parameters
        ----------
        file_bytes : bytes
            Содержимое файла.
        file_type : str
            MIME-тип: "image/jpeg", "image/png", "application/pdf".
        document_type : str
            Тип документа для выбора процессора: "waybill", "invoice" и т.д.

        Returns
        -------
        OCRResponse — pydantic-модель с полными данными.
        """
        start_ms = time.time()

        # Запускаем OCR в thread pool, чтобы не блокировать event loop
        ocr_result = await asyncio.get_event_loop().run_in_executor(
            None, self._run_ocr, file_bytes, file_type
        )

        # Выбираем процессор
        processor = self._processors.get(document_type)
        if processor is None:
            logger.warning(
                "Нет процессора для типа '%s', будет возвращён сырой текст",
                document_type,
            )
            extracted_data: Dict[str, Any] = {}
            confidence = 0.0
            warnings = [f"Unknown document_type '{document_type}', raw OCR only"]
        else:
            result = processor.process(ocr_result, file_type)
            extracted_data = result.get("extracted_data", {})
            confidence = result.get("confidence", 0.0)
            warnings = []

        elapsed_ms = int((time.time() - start_ms) * 1000)

        return OCRResponse(
            status=ProcessingStatus.SUCCESS if extracted_data else ProcessingStatus.PARTIAL,
            document_type=document_type,
            confidence=confidence,
            processing_time_ms=elapsed_ms,
            extracted_data=extracted_data,
            raw_text=ocr_result.get("full_text", ""),
            warnings=warnings,
            metadata={
                "lines_detected": len(ocr_result.get("lines", [])),
                "file_type": file_type,
                "ocr_backend": getattr(self._pipeline, "backend", None),
            },
        )

    # ------------------------------------------------------------------
    # Вспомогательный метод (синхронный, для thread pool)
    # ------------------------------------------------------------------

    def _run_ocr(self, file_bytes: bytes, file_type: str) -> Dict[str, Any]:
        """Конвертирует файл → numpy → OCR → словарь."""
        img = bytes_to_numpy(file_bytes, file_type)
        img = enhance_image(img)
        raw = self._pipeline.run(img)
        return parse_ocr_result(raw)
