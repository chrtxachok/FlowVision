#!/usr/bin/env python3
"""Альтернативный скрипт загрузки моделей"""

import os
import sys
import requests
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_file(url, dest_path):
    """Загрузка файла с прогресс-баром"""
    logger.info(f"Загрузка: {url}")
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    with open(dest_path, 'wb') as f:
        for data in response.iter_content(chunk_size=8192):
            f.write(data)
    
    logger.info(f"Сохранено: {dest_path}")

def manual_download_models():
    """Ручная загрузка моделей"""
    model_dir = Path("models")
    model_dir.mkdir(exist_ok=True)
    
    # Модели для русского языка
    models = {
        "det": {
            "url": "https://paddleocr.bj.bcebos.com/PP-OCRv4/russian/ch_PP-OCRv4_det_infer.tar",
            "name": "ch_PP-OCRv4_det_infer.tar"
        },
        "rec": {
            "url": "https://paddleocr.bj.bcebos.com/PP-OCRv4/russian/ch_PP-OCRv4_rec_infer.tar",
            "name": "ch_PP-OCRv4_rec_infer.tar"
        },
        "cls": {
            "url": "https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_cls_infer.tar",
            "name": "ch_ppocr_mobile_v2.0_cls_infer.tar"
        }
    }
    
    for model_type, model_info in models.items():
        dest_path = model_dir / model_info["name"]
        
        if dest_path.exists():
            logger.info(f"Модель {model_type} уже существует: {dest_path}")
            continue
        
        try:
            download_file(model_info["url"], dest_path)
            
            # Распаковка tar-архива
            import tarfile
            with tarfile.open(dest_path, 'r') as tar:
                tar.extractall(path=model_dir)
            
            logger.info(f"✓ Модель {model_type} распакована")
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке {model_type}: {e}")
    
    logger.info("Загрузка завершена!")

if __name__ == "__main__":
    manual_download_models()