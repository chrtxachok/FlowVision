"""
OCR Pipeline - основной пайплайн обработки документов.
"""

import logging
import time
from typing import Any, Dict, Optional

import structlog

from .preprocess import ImagePreprocessor
from .text_detection import TextDetector
from .layoutlm_extractor import LayoutLMExtractor
from .postprocess import TextPostprocessor

logger = structlog.get_logger()


class OCRPipeline:
    """
    Основной пайплайн OCR обработки документов.
    
    Этапы:
    1. Предобработка изображения
    2. Обнаружение текста (DBNet)
    3. Распознавание текста (PaddleOCR)
    4. Извлечение полей (LayoutLM)
    5. Постобработка текста
    """
    
    def __init__(
        self,
        language: str = "ru",
        extract_tables: bool = True,
        enhance_image: bool = True,
    ):
        """
        Инициализация OCR пайплайна.
        
        Args:
            language: Язык документа
            extract_tables: Извлекать таблицы
            enhance_image: Улучшать качество изображения
        """
        self.language = language
        self.extract_tables = extract_tables
        self.enhance_image = enhance_image
        
        # Инициализация компонентов
        self.preprocessor = ImagePreprocessor()
        self.text_detector = TextDetector()
        self.layoutlm_extractor = LayoutLMExtractor()
        self.postprocessor = TextPostprocessor()
        
        logger.info(
            "OCR Pipeline initialized",
            language=language,
            extract_tables=extract_tables,
        )
    
    def process(self, image_path: str) -> Dict[str, Any]:
        """
        Обработка документа через полный пайплайн.
        
        Args:
            image_path: Путь к изображению или URL
            
        Returns:
            Результат распознавания
        """
        start_time = time.time()
        
        try:
            # Этап 1: Предобработка
            logger.info("Stage 1: Image preprocessing")
            preprocessed_image = self.preprocessor.preprocess(
                image_path, 
                enhance=self.enhance_image
            )
            
            # Этап 2: Обнаружение текста
            logger.info("Stage 2: Text detection")
            text_regions = self.text_detector.detect(preprocessed_image)
            
            # Этап 3: Распознавание текста
            logger.info("Stage 3: Text recognition")
            recognized_texts = self.text_detector.recognize(
                preprocessed_image,
                text_regions,
                language=self.language
            )
            
            # Этап 4: Извлечение полей (LayoutLM)
            logger.info("Stage 4: Field extraction")
            extracted_fields = self.layoutlm_extractor.extract(
                preprocessed_image,
                recognized_texts,
                text_regions
            )
            
            # Этап 5: Постобработка
            logger.info("Stage 5: Postprocessing")
            final_fields = self.postprocessor.process(
                extracted_fields,
                recognized_texts
            )
            
            processing_time = time.time() - start_time
            
            result = {
                "status": "completed",
                "fields": final_fields,
                "raw_text": "\n".join([t["text"] for t in recognized_texts]),
                "processing_time": processing_time,
            }
            
            logger.info(
                "OCR Pipeline completed",
                processing_time=processing_time,
                fields_count=len(final_fields)
            )
            
            return result
            
        except Exception as e:
            logger.error("OCR Pipeline failed", error=str(e))
            return {
                "status": "failed",
                "error": str(e),
                "processing_time": time.time() - start_time,
            }
    
    def process_batch(self, image_paths: list) -> list:
        """
        Пакетная обработка нескольких документов.
        
        Args:
            image_paths: Список путей к изображениям
            
        Returns:
            Список результатов
        """
        results = []
        for image_path in image_paths:
            result = self.process(image_path)
            results.append(result)
        return results
