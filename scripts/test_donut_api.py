#!/usr/bin/env python3
"""
Скрипт для тестирования Donut API локально.

Использование:
  python scripts/test_donut_api.py --path static/image.jpg --doc-type waybill
  python scripts/test_donut_api.py --path document.pdf --doc-type invoice
"""

import argparse
import json
import logging
import time
from pathlib import Path

import numpy as np
from PIL import Image

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Добавляем родительскую директорию в path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.ocr.preprocess import bytes_to_numpy, enhance_image
from app.ocr.donut_extractor import DonutExtractor


def load_image(image_path: str | Path) -> np.ndarray:
    """Загружает изображение и преобразует в numpy array."""
    image_path = Path(image_path)
    
    if not image_path.exists():
        raise FileNotFoundError(f"Файл не найден: {image_path}")
    
    # Определяем MIME тип по расширению
    suffix = image_path.suffix.lower()
    mime_type = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.pdf': 'application/pdf',
    }.get(suffix, 'image/jpeg')
    
    # Читаем файл
    with open(image_path, 'rb') as f:
        file_bytes = f.read()
    
    # Конвертируем в numpy array
    image_array = bytes_to_numpy(file_bytes, mime_type)
    
    return image_array


def test_donut_extraction(
    image_path: str | Path,
    document_type: str = "invoice",
    device: str = "cpu",
):
    """Тестирует извлечение данных с помощью Donut."""
    
    logger.info("=" * 60)
    logger.info("Donut Extraction Test")
    logger.info("=" * 60)
    
    try:
        # 1. Загружаем модель
        logger.info(f"\n1. Загружаем модель '{settings.DONUT_MODEL_NAME}'...")
        start = time.time()
        
        extractor = DonutExtractor.from_pretrained(
            model_name_or_path=settings.DONUT_MODEL_NAME,
            device=device,
            cache_dir=settings.DONUT_CACHE_DIR,
        )
        
        load_time = time.time() - start
        logger.info(f"   ✓ Модель загружена за {load_time:.2f}s")
        
        # 2. Загружаем изображение
        logger.info(f"\n2. Загружаем изображение '{image_path}'...")
        image = load_image(image_path)
        logger.info(f"   ✓ Размер изображения: {image.shape}")
        
        # 3. Улучшаем изображение
        logger.info(f"\n3. Улучшаем изображение для OCR...")
        image = enhance_image(image)
        logger.info(f"   ✓ Обработано")
        
        # 4. Выбираем task prompt
        task_prompt = settings.DONUT_TASK_PROMPTS.get(
            document_type,
            settings.DONUT_TASK_PROMPTS.get("invoice", "<s_invoice>")
        )
        logger.info(f"\n4. Task prompt: {task_prompt}")
        
        # 5. Запускаем extraction
        logger.info(f"\n5. Запускаем extraction (device={device})...")
        start = time.time()
        
        result = extractor.extract(
            image=image,
            task_prompt=task_prompt,
            max_length=settings.DONUT_MAX_LENGTH,
            num_beams=settings.DONUT_NUM_BEAMS,
            temperature=settings.DONUT_TEMPERATURE,
        )
        
        extraction_time = time.time() - start
        logger.info(f"   ✓ Extraction выполнен за {extraction_time:.2f}s")
        
        # 6. Результаты
        logger.info(f"\n6. Результаты:")
        logger.info(f"   Confidence: {result['confidence']}")
        logger.info(f"   Raw text (first 300 chars):\n{result['text'][:300]}...")
        
        # 7. Парсим JSON если возможно
        logger.info(f"\n7. Попытка парсить JSON...")
        raw_text = result['text']
        start_idx = raw_text.find('{')
        end_idx = raw_text.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            json_str = raw_text[start_idx:end_idx + 1]
            try:
                parsed_data = json.loads(json_str)
                logger.info(f"   ✓ JSON распарсен успешно!")
                logger.info(f"\n   Извлеченные данные:")
                
                for key, value in parsed_data.items():
                    if isinstance(value, (dict, list)):
                        logger.info(f"     {key}: {str(value)[:100]}...")
                    else:
                        logger.info(f"     {key}: {value}")
                
                return {
                    "status": "success",
                    "extraction_time": extraction_time,
                    "load_time": load_time,
                    "extracted_data": parsed_data,
                    "raw_text": result['text'],
                }
            except json.JSONDecodeError as e:
                logger.warning(f"   ✗ JSON парсинг не удался: {e}")
                logger.info(f"\n   Raw text:")
                logger.info(result['text'])
                
                return {
                    "status": "success_but_json_parse_failed",
                    "extraction_time": extraction_time,
                    "load_time": load_time,
                    "raw_text": result['text'],
                }
        else:
            logger.warning("   ✗ JSON не найден в результате")
            logger.info(f"\n   Raw text:")
            logger.info(result['text'])
            
            return {
                "status": "success_but_no_json",
                "extraction_time": extraction_time,
                "load_time": load_time,
                "raw_text": result['text'],
            }
        
    except Exception as e:
        logger.error(f"✗ Ошибка: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
        }
    
    finally:
        logger.info("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Тест Donut extraction API",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    
    parser.add_argument(
        "--path",
        type=str,
        required=True,
        help="Путь к файлу документа (JPEG, PNG, PDF)",
    )
    
    parser.add_argument(
        "--doc-type",
        type=str,
        default="invoice",
        choices=["waybill", "invoice", "act", "upd"],
        help="Тип документа для правильного task prompt",
    )
    
    parser.add_argument(
        "--device",
        type=str,
        default=settings.DONUT_DEVICE,
        choices=["cpu", "cuda"],
        help="Device для выполнения (cpu или cuda)",
    )
    
    args = parser.parse_args()
    
    # Запускаем тест
    result = test_donut_extraction(
        image_path=args.path,
        document_type=args.doc_type,
        device=args.device,
    )
    
    # Выводим финальный результат
    print("\n" + "=" * 60)
    print("ИТОГОВЫЙ РЕЗУЛЬТАТ:")
    print(json.dumps(
        {k: v for k, v in result.items() if k != 'raw_text'},
        indent=2,
        ensure_ascii=False
    ))


if __name__ == "__main__":
    main()
