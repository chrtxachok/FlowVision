"""
Модуль предобработки изображений перед OCR.
Поддерживает JPEG, PNG и PDF (первая страница).
"""
import io
import logging
import numpy as np
import cv2
from PIL import Image, ImageEnhance

logger = logging.getLogger(__name__)


def bytes_to_numpy(file_bytes: bytes, file_type: str) -> np.ndarray:
    """
    Конвертирует байты файла в numpy-массив (BGR, для OpenCV).

    Поддерживаемые типы:
        - image/jpeg
        - image/png
        - application/pdf  (обрабатывается первая страница через PyMuPDF)
    """
    if file_type == "application/pdf":
        return _pdf_to_numpy(file_bytes)

    # JPEG / PNG → PIL → numpy
    img_pil = Image.open(io.BytesIO(file_bytes)).convert("RGB")
    img_np = np.array(img_pil)
    # PIL: RGB; OpenCV: BGR
    return cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)


def _pdf_to_numpy(file_bytes: bytes) -> np.ndarray:
    """Конвертирует первую страницу PDF в numpy-массив."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError(
            "Для обработки PDF установите PyMuPDF: pip install PyMuPDF"
        )

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    page = doc[0]
    # DPI 200 даёт хорошее качество без избыточного размера
    mat = fitz.Matrix(200 / 72, 200 / 72)
    pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
    img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, 3
    )
    return cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)


def enhance_image(img: np.ndarray) -> np.ndarray:
    """
    Улучшает качество изображения для OCR:
    - Конвертирует в оттенки серого
    - Применяет адаптивный порог (CLAHE)
    - Увеличивает резкость
    Возвращает BGR-изображение.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Адаптивное выравнивание гистограммы
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # Небольшое увеличение резкости через unsharp mask
    blurred = cv2.GaussianBlur(gray, (0, 0), sigmaX=3)
    gray = cv2.addWeighted(gray, 1.5, blurred, -0.5, 0)

    # Обратно в BGR для совместимости с PaddleOCR
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
