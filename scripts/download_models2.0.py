#!/usr/bin/env python3
"""
Надёжный скрипт загрузки моделей PaddleOCR для Windows
Автоматически обрабатывает обрывы соединения и проблемы с распаковкой
"""

import os
import sys
import requests
import tarfile
import shutil
from pathlib import Path
import logging
import time
from tqdm import tqdm  # Для прогресс-бара (установите: pip install tqdm)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('download_models.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Модели для русского языка (официальные ссылки от PaddlePaddle)
MODELS = {
    "det": {
        "url": "https://paddleocr.bj.bcebos.com/PP-OCRv4/english/en_PP-OCRv4_det_infer.tar",
        "expected_size": 3_000_000,  # ~3 MB
        "extract_dir": "en_PP-OCRv4_det_infer"
    },
    "rec": {
        "url": "https://paddleocr.bj.bcebos.com/PP-OCRv4/multilingual/Multilingual_PP-OCRv4_rec_infer.tar",
        "expected_size": 180_000_000,  # ~180 MB
        "extract_dir": "Multilingual_PP-OCRv4_rec_infer"
    },
    "cls": {
        "url": "https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_cls_infer.tar",
        "expected_size": 1_500_000,  # ~1.5 MB
        "extract_dir": "ch_ppocr_mobile_v2.0_cls_infer"
    }
}

def download_with_resume(url, dest_path, expected_size=None, max_retries=3):
    """Надёжная загрузка с возобновлением и проверкой размера"""
    for attempt in range(max_retries):
        try:
            # Проверяем, существует ли уже файл и его размер
            if os.path.exists(dest_path):
                current_size = os.path.getsize(dest_path)
                logger.info(f"Файл частично загружен: {current_size} байт")
            else:
                current_size = 0

            headers = {"Range": f"bytes={current_size}-"} if current_size > 0 else {}
            
            with requests.get(url, headers=headers, stream=True, timeout=60) as r:
                r.raise_for_status()
                
                mode = "ab" if current_size > 0 else "wb"
                total_size = int(r.headers.get('content-length', 0)) + current_size
                
                with open(dest_path, mode) as f:
                    with tqdm(
                        total=total_size,
                        initial=current_size,
                        unit='B',
                        unit_scale=True,
                        desc=os.path.basename(dest_path),
                        ncols=80
                    ) as pbar:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                pbar.update(len(chunk))
            
            # Проверка размера
            actual_size = os.path.getsize(dest_path)
            if expected_size and actual_size < expected_size:
                logger.warning(f"Файл слишком мал: {actual_size} байт (ожидалось минимум {expected_size})")
                if attempt < max_retries - 1:
                    logger.info(f"Повторная попытка загрузки ({attempt + 1}/{max_retries})...")
                    os.remove(dest_path)
                    time.sleep(2)
                    continue
                else:
                    raise ValueError(f"Файл повреждён после {max_retries} попыток")
            
            logger.info(f"✓ Загрузка завершена: {dest_path} ({actual_size / 1024 / 1024:.2f} МБ)")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке (попытка {attempt + 1}): {e}")
            if os.path.exists(dest_path):
                os.remove(dest_path)
            time.sleep(5)
    
    return False

def safe_extract_tar(tar_path, extract_path):
    """Безопасная распаковка tar-архива с обработкой ошибок Windows"""
    try:
        # Создаём временную директорию для распаковки
        temp_dir = Path(extract_path) / f".temp_extract_{os.getpid()}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Распаковка {tar_path} → {extract_path}")
        
        # Используем явный формат 'r' (без сжатия)
        with tarfile.open(tar_path, 'r') as tar:
            members = tar.getmembers()
            for member in tqdm(members, desc="Распаковка", ncols=80):
                try:
                    # Исправляем путь для Windows (заменяем / на \)
                    member.name = member.name.replace('/', '\\')
                    tar.extract(member, path=temp_dir)
                except Exception as e:
                    logger.warning(f"Пропускаем файл {member.name}: {e}")
        
        # Перемещаем файлы из временной директории в целевую
        target_dir = Path(extract_path)
        for item in temp_dir.iterdir():
            shutil.move(str(item), str(target_dir / item.name))
        
        # Удаляем временную директорию
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        logger.info(f"✓ Распаковка завершена: {extract_path}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка распаковки: {e}")
        return False

def download_all_models():
    """Загрузка и распаковка всех моделей"""
    model_dir = Path("models")
    model_dir.mkdir(exist_ok=True)
    
    logger.info("=" * 60)
    logger.info("Начало загрузки моделей PaddleOCR для русского языка")
    logger.info("=" * 60)
    
    results = {}
    
    for model_name, config in MODELS.items():
        logger.info(f"\n--- Загрузка модели: {model_name.upper()} ---")
        
        tar_path = model_dir / f"{config['extract_dir']}.tar"
        extract_path = model_dir / config['extract_dir']
        
        # Пропускаем, если модель уже распакована
        if extract_path.exists() and (extract_path / "inference.pdmodel").exists():
            logger.info(f"✓ Модель {model_name} уже установлена — пропускаем")
            results[model_name] = True
            continue
        
        # Загрузка файла
        success = download_with_resume(
            config['url'],
            tar_path,
            expected_size=config['expected_size']
        )
        
        if not success:
            logger.error(f"✗ Не удалось загрузить модель {model_name}")
            results[model_name] = False
            continue
        
        # Распаковка
        success = safe_extract_tar(tar_path, extract_path)
        results[model_name] = success
        
        # Удаляем .tar после успешной распаковки (экономим место)
        if success and tar_path.exists():
            tar_path.unlink()
            logger.info(f"Удалён временный файл: {tar_path.name}")
    
    # Итоговый отчёт
    logger.info("\n" + "=" * 60)
    logger.info("Итог загрузки моделей:")
    logger.info("=" * 60)
    for model_name, success in results.items():
        status = "✓ УСПЕШНО" if success else "✗ ОШИБКА"
        logger.info(f"{model_name.upper():10} : {status}")
    
    if all(results.values()):
        logger.info("\n✅ Все модели успешно загружены и распакованы!")
        logger.info(f"Модели расположены в: {model_dir.absolute()}")
        return True
    else:
        logger.error("\n❌ Некоторые модели не были загружены. Проверьте логи.")
        return False

if __name__ == "__main__":
    # Проверка на антивирус/блокировку (частая проблема в Windows)
    try:
        test_file = Path("models") / ".write_test.tmp"
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text("test")
        test_file.unlink()
    except Exception as e:
        logger.warning(f"⚠️ Возможна проблема с правами записи в директорию 'models': {e}")
        logger.warning("Попробуйте запустить командную строку от имени Администратора")
    
    success = download_all_models()
    
    if success:
        print("\n" + "=" * 60)
        print("✅ Модели готовы к использованию!")
        print("=" * 60)
        print("\nСледующие шаги:")
        print("1. Убедитесь, что в директории 'models' есть папки:")
        print("   - ch_PP-OCRv4_det_infer")
        print("   - ch_PP-OCRv4_rec_infer")
        print("   - ch_ppocr_mobile_v2.0_cls_infer")
        print("2. Запустите тестовый скрипт:")
        print("   python test_ocr.py")
    else:
        print("\n❌ Загрузка не завершена. Проверьте файл download_models.log")
        print("Возможные решения:")
        print("  • Проверьте интернет-соединение")
        print("  • Отключите антивирус на время загрузки")
        print("  • Запустите командную строку от имени Администратора")
        print("  • Попробуйте загрузить модели вручную с сайта:")
        print("    https://github.com/PaddlePaddle/PaddleOCR/blob/release/2.7/doc/doc_en/models_list_en.md")