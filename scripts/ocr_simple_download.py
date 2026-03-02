#!/usr/bin/env python3
"""
Простой скрипт инициализации PaddleOCR с тестовым распознаванием.
Запускать из корня проекта: python scripts/ocr_simple_download.py
"""
from pathlib import Path
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Пути к локальным моделям
DET_MODEL_DIR = Path("models/en_PP-OCRv4_det_infer")
REC_MODEL_DIR = Path("models/Multilingual_PP-OCRv4_rec_infer")
CLS_MODEL_DIR = Path("models/ch_ppocr_mobile_v2.0_cls_infer")


def check_model(model_dir: Path) -> bool:
    """Проверяет, что директория модели существует и содержит inference.pdmodel."""
    pdmodel = model_dir / "inference.pdmodel"
    if model_dir.exists() and pdmodel.exists():
        logger.info("✓ Модель найдена: %s", model_dir)
        return True
    else:
        logger.warning("⚠️ Модель не найдена: %s", model_dir)
        return False


def main():
    from paddleocr import PaddleOCR

    logger.info("Инициализация PaddleOCR...")
    logger.info("Загрузка моделей может занять 5-10 минут при первом запуске...")

    # Проверяем наличие локальных моделей
    local_ready = all([
        check_model(DET_MODEL_DIR),
        check_model(REC_MODEL_DIR),
        check_model(CLS_MODEL_DIR),
    ])

    try:
        if local_ready:
            logger.info("Используем локальные модели.")
            ocr = PaddleOCR(
                det_model_dir=str(DET_MODEL_DIR),
                rec_model_dir=str(REC_MODEL_DIR),
                cls_model_dir=str(CLS_MODEL_DIR),
                use_angle_cls=True,
                show_log=False,
            )
        else:
            logger.info(
                "Локальные модели не найдены — PaddleOCR загрузит их автоматически (lang='ru').\n"
                "  Чтобы загрузить заранее, запустите: python scripts/download_models.py"
            )
            ocr = PaddleOCR(
                lang="ru",
                use_angle_cls=True,
                show_log=False,
            )

        logger.info("\n✅ Инициализация прошла успешно!")
        logger.info("  Модели готовы к работе.")

        # Тестовое распознавание на публичной картинке
        logger.info("\nТестовое распознавание...")
        test_url = "https://github.com/PaddlePaddle/PaddleOCR/raw/release/2.6/doc/imgs/12.jpg"
        result = ocr.ocr(test_url, cls=True)

        if result and result[0]:
            logger.info("\n✅ Тест пройден! Пример распознанного текста:")
            for line in result[0]:
                text = line[1][0]
                confidence = line[1][1]
                logger.info("  • %s (уверенность: %.2f%%)", text, confidence * 100)
        else:
            logger.warning("⚠️ Распознавание не вернуло результатов (но модели загружены)")

    except Exception as e:
        logger.error("\n❌ Ошибка при инициализации: %s: %s", type(e).__name__, e)
        logger.error("Возможные решения:")
        logger.error("  1. pip install --upgrade paddlepaddle paddleocr")
        logger.error("  2. Скачайте модели вручную: python scripts/download_models.py")
        logger.error("  3. Проверьте интернет-соединение (для автозагрузки)")
        raise


if __name__ == "__main__":
    main()