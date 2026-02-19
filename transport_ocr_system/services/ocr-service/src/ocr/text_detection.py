"""
Обнаружение и распознавание текста.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import structlog
from paddleocr import PaddleOCR

logger = structlog.get_logger()


class TextDetector:
    """
    Обнаружение и распознавание текста с использованием PaddleOCR.
    
    Компонент объединяет:
    - DBNet для обнаружения текстовых регионов
    - CRNN для распознавания текста
    """
    
    def __init__(
        self,
        use_angle_cls: bool = True,
        lang: str = "ru",
        use_gpu: bool = False,
        confidence_threshold: float = 0.7,
    ):
        """
        Инициализация детектора текста.
        
        Args:
            use_angle_cls: Использовать классификатор углов
            lang: Язык распознавания
            use_gpu: Использовать GPU
            confidence_threshold: Порог достоверности
        """
        self.lang = lang
        self.confidence_threshold = confidence_threshold
        
        # Инициализация PaddleOCR
        self.ocr = PaddleOCR(
            use_angle_cls=use_angle_cls,
            lang=lang,
            use_gpu=use_gpu,
            show_log=False,
            det_db_thresh=confidence_threshold,
            rec_batch_num=6,
        )
        
        logger.info(
            "TextDetector initialized",
            lang=lang,
            use_gpu=use_gpu,
            confidence_threshold=confidence_threshold,
        )
    
    def detect(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Обнаружение текстовых регионов на изображении.
        
        Args:
            image: Изображение (numpy array)
            
        Returns:
            Список текстовых регионов с координатами
        """
        try:
            # Обнаружение текста
            result = self.ocr.ocr(image, cls=True)
            
            if not result or not result[0]:
                logger.warning("No text detected in image")
                return []
            
            regions = []
            for line in result[0]:
                box = line[0]  # Координаты bounding box
                text_info = line[1]
                
                region = {
                    "text": text_info[0],
                    "confidence": text_info[1],
                    "bbox": self._box_to_dict(box),
                    "angle": text_info[2] if len(text_info) > 2 else 0,
                }
                regions.append(region)
            
            logger.info("Text detection completed", regions_count=len(regions))
            return regions
            
        except Exception as e:
            logger.error("Text detection failed", error=str(e))
            return []
    
    def recognize(
        self, 
        image: np.ndarray,
        regions: List[Dict[str, Any]],
        language: str = "ru"
    ) -> List[Dict[str, Any]]:
        """
        Распознавание текста в указанных регионах.
        
        Args:
            image: Изображение
            regions: Список регионов для распознавания
            language: Язык
            
        Returns:
            Список распознанных текстов с метаданными
        """
        if not regions:
            # Если регионы не переданы, выполняем полное распознавание
            result = self.ocr.ocr(image, cls=True)
            
            if not result or not result[0]:
                return []
            
            recognized = []
            for line in result[0]:
                box = line[0]
                text_info = line[1]
                
                recognized.append({
                    "text": text_info[0],
                    "confidence": text_info[1],
                    "bbox": self._box_to_dict(box),
                    "page": 1,
                })
            
            return recognized
        
        # Распознавание текста в каждом регионе
        recognized = []
        for i, region in enumerate(regions):
            # Обрезка региона
            bbox = region.get("bbox", {})
            x_min = int(bbox.get("x_min", 0))
            y_min = int(bbox.get("y_min", 0))
            x_max = int(bbox.get("x_max", 0))
            y_max = int(bbox.get("y_max", 0))
            
            # Обрезка изображения
            cropped = image[y_min:y_max, x_min:x_max]
            
            if cropped.size == 0:
                continue
            
            # Распознавание текста в регионе
            result = self.ocr.ocr(cropped, cls=True)
            
            if result and result[0]:
                for line in result[0]:
                    text_info = line[1]
                    recognized.append({
                        "text": text_info[0],
                        "confidence": text_info[1],
                        "bbox": bbox,
                        "region_id": i,
                        "page": 1,
                    })
        
        logger.info("Text recognition completed", texts_count=len(recognized))
        return recognized
    
    def _box_to_dict(self, box: List[List[float]]) -> Dict[str, float]:
        """
        Конвертация bounding box в словарь.
        
        Args:
            box: Координаты [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            
        Returns:
            Словарь с координатами
        """
        xs = [point[0] for point in box]
        ys = [point[1] for point in box]
        
        return {
            "x_min": min(xs),
            "y_min": min(ys),
            "x_max": max(xs),
            "y_max": max(ys),
            "width": max(xs) - min(xs),
            "height": max(ys) - min(ys),
        }
    
    def detect_tables(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Обнаружение таблиц на изображении.
        
        Args:
            image: Изображение
            
        Returns:
            Список найденных таблиц
        """
        # Используем PaddleOCR для поиска таблиц
        # В реальной реализации можно использовать TableNet или другой специализированный метод
        
        result = self.ocr.ocr(image, cls=True)
        
        if not result or not result[0]:
            return []
        
        # Простая эвристика: таблицы имеют много горизонтальных линий
        # Здесь должна быть более сложная логика
        tables = []
        
        return tables
