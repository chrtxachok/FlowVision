from paddleocr import PaddleOCR
from typing import Dict, List, Any
import cv2
import numpy as np
from io import BytesIO
from PIL import Image
import logging

logger = logging.getLogger(__name__)

class TextExtractor:
    """Извлечение текста с использованием PaddleOCR"""
    
    def __init__(self):
        """Инициализация модели"""
        logger.info("Initializing PaddleOCR...")
        self.ocr = PaddleOCR(
            use_angle_cls=True,
            lang='ru',
            det_model_dir='models/paddle_det',
            rec_model_dir='models/paddle_rec',
            use_gpu=False  # Можно включить, если есть GPU
        )
        logger.info("PaddleOCR initialized")
    
    def extract_text(self, image_ bytes, image_type: str) -> Dict[str, Any]:
        """
        Извлечение текста из изображения или PDF
        
        Args:
            image_ байты изображения
            image_type: MIME-тип (image/jpeg, application/pdf)
            
        Returns:
            Словарь с результатами распознавания
        """
        try:
            # Конвертация в изображение
            image = self._convert_to_image(image_data, image_type)
            
            # Предобработка
            image = self._preprocess_image(image)
            
            # Распознавание
            result = self.ocr.ocr(image, cls=True)
            
            # Обработка результата
            extracted = self._process_ocr_result(result)
            
            return extracted
            
        except Exception as e:
            logger.error(f"Text extraction error: {e}")
            return {
                "full_text": "",
                "lines": [],
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _convert_to_image(self, image_ bytes, image_type: str) -> np.ndarray:
        """Конвертация в формат OpenCV"""
        if image_type == "application/pdf":
            # Для PDF конвертируем первую страницу
            from pdf2image import convert_from_bytes
            images = convert_from_bytes(image_data)
            image = np.array(images[0])
        else:
            # Для изображений
            image = np.array(Image.open(BytesIO(image_data)))
        
        # Конвертация в BGR (OpenCV формат)
        if len(image.shape) == 3 and image.shape[2] == 4:  # RGBA
            image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
        elif len(image.shape) == 2:  # Grayscale
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:  # RGB
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        
        return image
    
    def _preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Предобработка изображения"""
        # 1. Масштабирование, если слишком большое
        max_dim = 4096
        h, w = image.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            image = cv2.resize(image, (int(w * scale), int(h * scale)))
        
        # 2. Улучшение контраста (CLAHE)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        lab = cv2.merge((l, a, b))
        image = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        # 3. Удаление шума
        image = cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
        
        return image
    
    def _process_ocr_result(self, result: List) -> Dict[str, Any]:
        """Обработка результата распознавания"""
        lines = []
        full_text = ""
        total_confidence = 0.0
        line_count = 0
        
        if result and len(result) > 0:
            for line in result[0]:
                if line is None:
                    continue
                
                # Структура: [[координаты], (текст, уверенность)]
                bbox = line[0]
                text = line[1][0]
                confidence = line[1][1]
                
                lines.append({
                    "text": text,
                    "confidence": confidence,
                    "bbox": bbox
                })
                
                full_text += text + "\n"
                total_confidence += confidence
                line_count += 1
        
        avg_confidence = total_confidence / line_count if line_count > 0 else 0.0
        
        return {
            "full_text": full_text.strip(),
            "lines": lines,
            "confidence": avg_confidence,
            "line_count": line_count
        }