"""
Предобработка изображений для OCR.
"""

import io
import logging
from typing import Optional, Tuple, Union

import cv2
import numpy as np
import structlog
from PIL import Image

logger = structlog.get_logger()


class ImagePreprocessor:
    """
    Предобработчик изображений для улучшения качества OCR.
    
    Операции:
    - Контрастирование
    - Удаление шума
    - Поворот (deskew)
    - Удаление границ
    - Изменение разрешения
    """
    
    def __init__(
        self,
        target_dpi: int = 300,
        enhance_contrast: bool = True,
        denoise: bool = True,
        deskew: bool = True,
        remove_borders: bool = True,
    ):
        """
        Инициализация предобработчика.
        
        Args:
            target_dpi: Целевое разрешение DPI
            enhance_contrast: Улучшать контраст
            denoise: Удалять шум
            deskew: Поворачивать изображение
            remove_borders: Удалять границы
        """
        self.target_dpi = target_dpi
        self.enhance_contrast = enhance_contrast
        self.denoise = denoise
        self.deskew = deskew
        self.remove_borders = remove_borders
        
        logger.info(
            "ImagePreprocessor initialized",
            target_dpi=target_dpi,
        )
    
    def preprocess(
        self, 
        image_source: Union[str, bytes, np.ndarray],
        enhance: bool = True
    ) -> np.ndarray:
        """
        Полный цикл предобработки изображения.
        
        Args:
            image_source: Путь к файлу, байты или numpy массив
            enhance: Применять улучшения
            
        Returns:
            Предобработанное изображение
        """
        # Загрузка изображения
        image = self._load_image(image_source)
        
        if not enhance:
            return image
        
        logger.info("Starting image preprocessing")
        
        # Удаление границ
        if self.remove_borders:
            image = self._remove_borders(image)
        
        # Поворот
        if self.deskew:
            image = self._deskew(image)
        
        # Удаление шума
        if self.denoise:
            image = self._denoise(image)
        
        # Улучшение контраста
        if self.enhance_contrast:
            image = self._enhance_contrast(image)
        
        # Изменение разрешения
        image = self._resize_to_dpi(image)
        
        logger.info("Image preprocessing completed")
        return image
    
    def _load_image(self, source: Union[str, bytes, np.ndarray]) -> np.ndarray:
        """Загрузка изображения из различных источников."""
        if isinstance(source, str):
            # URL или путь к файлу
            if source.startswith("http"):
                import requests
                response = requests.get(source)
                image = Image.open(io.BytesIO(response.content))
                return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            else:
                return cv2.imread(source)
        elif isinstance(source, bytes):
            image = Image.open(io.BytesIO(source))
            return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        else:
            return source
    
    def _remove_borders(self, image: np.ndarray) -> np.ndarray:
        """Удаление черных/белых границ."""
        # Преобразование в градации серого
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Бинаризация
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        
        # Поиск контуров
        contours, _ = cv2.findContours(
            binary, 
            cv2.RETR_EXTERNAL, 
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        if contours:
            # Находим максимальный контур
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # Обрезаем с небольшим отступом
            margin = 5
            return image[
                y + margin:y + h - margin,
                x + margin:x + w - margin
            ]
        
        return image
    
    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """Поворот изображения по линиям текста."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Бинаризация
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Поиск горизонтальных линий
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 1))
        detected_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        
        # Поиск углов
        coords = np.column_stack(np.where(detected_lines > 0))
        
        if len(coords) > 0:
            angle = cv2.minAreaRect(coords)[-1]
            
            # Коррекция угла
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle
            
            if abs(angle) > 0.5:
                (h, w) = image.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                image = cv2.warpAffine(
                    image, M, (w, h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE
                )
        
        return image
    
    def _denoise(self, image: np.ndarray) -> np.ndarray:
        """Удаление шума."""
        return cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
    
    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Улучшение контраста с помощью CLAHE."""
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # CLAHE для канала L
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        
        lab = cv2.merge([l, a, b])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    
    def _resize_to_dpi(self, image: np.ndarray) -> np.ndarray:
        """Изменение размера до целевого DPI."""
        # Текущий размер
        height, width = image.shape[:2]
        
        # Целевой размер для 300 DPI (приблизительно)
        scale_factor = self.target_dpi / 96  # 96 - стандартное экранное DPI
        
        if scale_factor > 1:
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        return image
    
    def to_bytes(self, image: np.ndarray, format: str = "JPEG") -> bytes:
        """Конвертация изображения в байты."""
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
        buffer = io.BytesIO()
        pil_image.save(buffer, format=format)
        return buffer.getvalue()
