#!/usr/bin/env python3
"""Скрипт для загрузки моделей PaddleOCR"""

import os
from paddleocr import PaddleOCR
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_models():
    """Загрузка моделей для русского языка"""
    logger.info("Downloading PaddleOCR models...")
    
    # Создание директории для моделей
    model_dir = "models"
    os.makedirs(model_dir, exist_ok=True)
    
    # Инициализация для загрузки моделей
    ocr = PaddleOCR(
        lang='ru',
        det=True,
        rec=True,
        cls=True,
        use_gpu=False,
        download=True
    )
    
    logger.info("Models downloaded successfully!")
    logger.info(f"Models location: {os.path.abspath(model_dir)}")

if __name__ == "__main__":
    download_models()
    