import os
import sys
import tarfile
import urllib.request
import logging
from pathlib import Path

# Настроим логирование
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "models"

# Ссылки на актуальные модели PP-OCRv4 / v3
MODELS = {
    "det": {
        "url": "https://paddleocr.bcebos.com/PP-OCRv4/english/en_PP-OCRv4_det_infer.tar",  # или v3 multilingual выше
        "dirname": "ch_PP-OCRv3_det_ml_infer"
    },
    "rec": {
        "url": "https://paddleocr.bj.bcebos.com/PP-OCRv4/multilingual/Multilingual_PP-OCRv4_rec_infer.tar",
        "dirname": "Multilingual_PP-OCRv4_rec_infer"
    },
    "cls": {
       "url": "https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_cls_infer.tar",
        "dirname": "ch_ppocr_mobile_v2.0_cls_infer"
    }
}


def download_file(url: str, filepath: Path) -> bool:
    """Загружает файл по URL с прогрессом."""
    logger.info(f"Загрузка {url}...")
    try:
        def reporthook(blocknum, blocksize, totalsize):
            readsofar = blocknum * blocksize
            if totalsize > 0:
                percent = readsofar * 100 / totalsize
                sys.stdout.write(f"\rЗагружено {readsofar // 1024} KB / {totalsize // 1024} KB ({percent:.1f}%)")
                sys.stdout.flush()
            else:
                sys.stdout.write(f"\rЗагружено {readsofar // 1024} KB")
                sys.stdout.flush()

        urllib.request.urlretrieve(url, str(filepath), reporthook)
        sys.stdout.write("\n")
        logger.info(f"Скачан {filepath.name}")
        return True
    except Exception as e:
        logger.error(f"Ошибка загрузки {url}: {e}")
        return False

def extract_tar(filepath: Path, extract_to: Path) -> bool:
    """Распаковывает .tar."""
    logger.info(f"Распаковка {filepath.name}...")
    try:
        with tarfile.open(filepath, "r") as tar:
            tar.extractall(path=extract_to)
        logger.info(f"Распаковано в {extract_to}")
        return True
    except Exception as e:
        logger.error(f"Ошибка распаковки {filepath}: {e}")
        return False

def is_model_valid(model_dir: Path) -> bool:
    """Проверяет наличие ключевых файлов модели (inference.pdmodel и inference.pdiparams)."""
    required_files = {"inference.pdmodel", "inference.pdiparams"}
    if not model_dir.exists():
        return False
    existing = {f.name for f in model_dir.rglob("*") if f.is_file()}
    return required_files.issubset(existing)

def setup_models(force_download: bool = False):
    """Скачивает/обновляет модели."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    success_count = 0
    for model_type, info in MODELS.items():
        url = info["url"]
        dirname = info["dirname"]
        target_dir = MODEL_DIR / dirname
        
        logger.info(f"--- Модель: {model_type.upper()} ---")
        
        if not force_download and target_dir.exists() and is_model_valid(target_dir):
            logger.info(f"Модель {model_type} валидна в {target_dir}. Пропуск.")
            success_count += 1
            continue

        tar_path = MODEL_DIR / f"{dirname}.tar"
        
        if download_file(url, tar_path):
            # Очищаем старую директорию
            if target_dir.exists():
                import shutil
                shutil.rmtree(target_dir)
            
            if extract_tar(tar_path, MODEL_DIR):
                if is_model_valid(target_dir):
                    success_count += 1
                    logger.info(f"Модель {model_type} готова.")
                else:
                    logger.warning(f"Модель {model_type} распакована, но файлы невалидны.")
            
            tar_path.unlink(missing_ok=True)
        else:
            logger.error(f"Не удалось подготовить {model_type}.")

    if success_count == len(MODELS):
        logger.info("=" * 50)
        logger.info("✨ Все модели установлены! ✨")
        logger.info("=" * 50)
    else:
        logger.warning(f"Успех: {success_count}/{len(MODELS)}. Проверьте логи.")

if __name__ == "__main__":
    setup_models()