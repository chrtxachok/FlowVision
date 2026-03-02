"""
Центральный OCR-конвейер.

Поддерживает backends:
  - easyocr (по умолчанию): модели скачиваются автоматически
  - paddleocr (legacy): PaddleOCR v3 (PaddleX backend), при необходимости — локальные модели в models/

Публичный контракт:
  - `run(image: np.ndarray)` возвращает raw-результат backend'а
  - `app.ocr.postprocess.parse_ocr_result()` приводит raw-результат к общему формату:
      {"full_text": str, "lines": [...], "blocks": [...]}
"""
import logging
from pathlib import Path
from typing import Any, List

import numpy as np

logger = logging.getLogger(__name__)


def _model_dir_valid(path: Path) -> bool:
    """True, если директория содержит inference.pdmodel или model.pdmodel."""
    if not path.exists():
        return False
    return any(path.glob("*.pdmodel"))


class OCRPipeline:
    """
    Обёртка над OCR backend'ом (easyocr/paddleocr).
    """

    def __init__(
        self,
        backend: str = "easyocr",
        text_detection_model_dir: Path | None = None,
        text_recognition_model_dir: Path | None = None,
        textline_orientation_model_dir: Path | None = None,
        lang: str = "ru",
        device: str = "cpu",
        easyocr_languages: List[str] | None = None,
    ):
        requested_backend = (backend or "easyocr").lower().strip()
        self.device = (device or "cpu").lower().strip()
        actual_backend, engine = self._init_ocr(
            requested_backend,
            text_detection_model_dir,
            text_recognition_model_dir,
            textline_orientation_model_dir,
            lang,
            self.device,
            easyocr_languages,
        )
        self.backend = actual_backend
        self._ocr = engine
        logger.info("OCRPipeline успешно инициализирован (backend=%s, device=%s)", self.backend, self.device)

    # ------------------------------------------------------------------
    # Инициализация
    # ------------------------------------------------------------------

    @staticmethod
    def _init_ocr(
        backend: str,
        det_dir,
        rec_dir,
        cls_dir,
        lang: str,
        device: str,
        easyocr_languages: List[str] | None,
    ) -> tuple[str, Any]:
        """Создаёт объект OCR backend'а с учётом настроек."""
        if backend == "easyocr":
            try:
                return "easyocr", OCRPipeline._init_easyocr(lang=lang, device=device, languages=easyocr_languages)
            except ImportError as exc:
                logger.warning("EasyOCR выбран, но недоступен (%s). Пытаемся использовать paddleocr.", exc)
                return "paddleocr", OCRPipeline._init_paddleocr(det_dir=det_dir, rec_dir=rec_dir, cls_dir=cls_dir, lang=lang)
        if backend == "paddleocr":
            return "paddleocr", OCRPipeline._init_paddleocr(det_dir=det_dir, rec_dir=rec_dir, cls_dir=cls_dir, lang=lang)
        raise ValueError(f"Unsupported OCR_BACKEND='{backend}'. Use 'easyocr' or 'paddleocr'.")

    @staticmethod
    def _init_easyocr(lang: str, device: str, languages: List[str] | None):
        """Инициализация EasyOCR Reader."""
        try:
            import easyocr  # type: ignore
        except Exception as exc:
            raise ImportError(
                "EasyOCR не установлен. Установите зависимости: pip install easyocr"
            ) from exc

        langs = languages or [lang]
        gpu = device == "gpu"
        logger.info("Инициализация EasyOCR (langs=%s, gpu=%s)...", ",".join(langs), gpu)
        return easyocr.Reader(langs, gpu=gpu)

    @staticmethod
    def _init_paddleocr(det_dir, rec_dir, cls_dir, lang: str):
        """Создаёт объект PaddleOCR v3 с учётом доступности локальных моделей."""
        from paddleocr import PaddleOCR  # type: ignore

        # Общие параметры: отключаем doc preprocessor.
        # use_doc_orientation_classify и use_doc_unwarping загружают дополнительные
        # тяжёлые модели (PP-LCNet, UVDoc), которые не нужны для накладных.
        # Их отключение ускоряет старт и устраняет ошибки с кешем.
        shared = dict(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,  # PP-LCNet не загружается на Windows (пустой inference.json)
        )

        # Проверяем, есть ли все три директории с моделями
        use_local = (
            det_dir is not None
            and rec_dir is not None
            and _model_dir_valid(det_dir)
            and _model_dir_valid(rec_dir)
        )

        if use_local:
            logger.info(
                "Используем локальные модели:\n  det=%s\n  rec=%s\n  cls=%s",
                det_dir, rec_dir, cls_dir,
            )
            kwargs = {
                **shared,
                "text_detection_model_dir": str(det_dir),
                "text_recognition_model_dir": str(rec_dir),
            }
            # Классификатор ориентации строк — опциональный
            if cls_dir and _model_dir_valid(cls_dir):
                kwargs["textline_orientation_model_dir"] = str(cls_dir)
            return PaddleOCR(**kwargs)

        else:
            logger.info(
                "Локальные модели не найдены (или USE_LOCAL_MODELS=False). "
                "PaddleOCR загрузит модели автоматически (lang=%s, PP-OCRv5). "
                "Первый запуск может занять несколько минут.",
                lang,
            )
            return PaddleOCR(lang=lang, **shared)

    # ------------------------------------------------------------------
    # Публичный интерфейс
    # ------------------------------------------------------------------

    def run(self, image: np.ndarray) -> List[Any]:
        """
        Запускает OCR на изображении.

        Parameters
        ----------
        image : np.ndarray
            Изображение в формате BGR (OpenCV) или RGB.

        Returns
        -------
        Raw-результат backend'а.
        Передайте результат в `app.ocr.postprocess.parse_ocr_result()`.
        """
        if self.backend == "easyocr":
            # EasyOCR ожидает RGB / путь к файлу; для numpy подадим RGB.
            # Весь код пайплайна выше использует BGR (OpenCV), поэтому конвертируем.
            import cv2
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            # detail=1: bbox + text + conf (нужно для дальнейшего парсинга)
            return list(self._ocr.readtext(rgb, detail=1, paragraph=False))

        # PaddleOCR v3: predict() — актуальный метод (ocr() deprecated)
        results = self._ocr.predict(image)
        return list(results)

    @classmethod
    def from_settings(cls) -> "OCRPipeline":
        """
        Фабричный метод: создаёт OCRPipeline из настроек приложения.
        """
        from app.config import settings

        backend = (settings.OCR_BACKEND or "easyocr").lower().strip()

        det = rec = cls_ = None
        if backend == "paddleocr":
            if settings.USE_LOCAL_MODELS:
                det = settings.DETECT_MODEL_PATH
                rec = settings.RECOGNIZE_MODEL_PATH
                cls_ = settings.CLASSIFY_MODEL_PATH
            else:
                # Принудительная онлайн-загрузка
                det = rec = cls_ = None

        return cls(
            backend=backend,
            text_detection_model_dir=det,
            text_recognition_model_dir=rec,
            textline_orientation_model_dir=cls_,
            lang=settings.LANGUAGE,
            device=settings.OCR_DEVICE,
            easyocr_languages=getattr(settings, "EASYOCR_LANGUAGES", None),
        )
