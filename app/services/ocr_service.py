"""
OCR-сервис — тонкая обёртка над логикой извлечения полей из logika.py.

Полностью повторяет pipeline из test_gui.py:
    extractor = WaybillExtractor(json_path="project-1-at-2026-04-18-05-40-eb2e8e7a.json")
    result = extractor.extract(paths)   # paths — 1 или 2 пути к изображениям

API превращён в HTTP-обёртку: входные файлы сохраняются во временные файлы,
передаются в extractor.extract(), результат возвращается как есть.
"""
import asyncio
import logging
import os
import tempfile
import time
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class OCRService:
    """Точка входа для обработки документов через WaybillExtractor (logika.py)."""

    def __init__(self):
        from app.config import settings

        # Путь к JSON-разметке (как в test_gui.py)
        self._json_path = str(settings.LABEL_STUDIO_JSON)
        # Директория, где лежат .pkl модели (field_classifier.pkl, scaler.pkl, field_coords.pkl)
        self._model_dir = str(settings.LOGIKA_MODEL_DIR)

        logger.info(
            "Инициализация OCRService (logika.WaybillExtractor, model_dir=%s, json=%s)...",
            self._model_dir,
            self._json_path,
        )

        # Инициализируем экстрактор один раз (загрузка EasyOCR + обученной модели),
        # точно так же, как это делает test_gui.py при старте.
        from logika import WaybillExtractor

        json_path = self._json_path if os.path.exists(self._json_path) else None
        self._extractor = WaybillExtractor(
            json_path=json_path,
            model_dir=self._model_dir,
        )

        logger.info("OCRService готов (logika.WaybillExtractor)")

    async def process_document(
        self, files: List[Tuple[bytes, str]], document_type: str = "waybill"
    ) -> Dict[str, Any]:
        """
        Обрабатывает 1 или 2 изображения.

        :param files: список кортежей (file_bytes, filename) — 1 или 2 элемента
        :param document_type: тип документа (для метаданных, по умолчанию waybill)
        :return: словарь с результатом, аналогичный выводу extractor.extract()
        """
        start_ms = time.time()

        extracted_data = await asyncio.get_event_loop().run_in_executor(
            None, self._run_extract, files
        )

        elapsed_ms = int((time.time() - start_ms) * 1000)

        return {
            "status": "success" if extracted_data else "partial",
            "document_type": document_type,
            "processing_time_ms": elapsed_ms,
            "pages_processed": len(files),
            "extracted_data": extracted_data,
        }

    def _run_extract(self, files: List[Tuple[bytes, str]]) -> Dict[str, Any]:
        """
        Сохраняет загруженные файлы во временные файлы и вызывает
        extractor.extract(paths) — точно так же, как в test_gui.py.
        """
        tmp_paths: List[str] = []
        try:
            for file_bytes, filename in files:
                suffix = os.path.splitext(filename)[1] or ".jpg"
                fd, tmp_path = tempfile.mkstemp(suffix=suffix)
                with os.fdopen(fd, "wb") as f:
                    f.write(file_bytes)
                tmp_paths.append(tmp_path)

            # Тот же вызов, что и в test_gui.py: extractor.extract(paths)
            result = self._extractor.extract(tmp_paths)
            return result or {}
        finally:
            for p in tmp_paths:
                try:
                    os.remove(p)
                except OSError:
                    pass
