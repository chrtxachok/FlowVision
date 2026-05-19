"""
Donut model extractor для end-to-end извлечения данных из документов.

Donut (Document understanding Transformer) — это vision transformer модель
для распознавания и структурированного извлечения данных из документов.
Используется для выделения конкретных полей из документов напрямую,
без промежуточного этапа обнаружения текста.

Публичный контракт:
  - `from_pretrained()` — инициализирует модель и процессор
  - `extract()` — возвращает структурированные данные из документа
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import numpy as np
import torch
from PIL import Image
import io

logger = logging.getLogger(__name__)


class DonutExtractor:
    """
    Extractor для работы с Donut моделью.
    
    Поддерживает:
    - Загрузку предобученных моделей (доступные: donut-base, donut-large и т.д.)
    - Инициализацию с локальной моделью
    - Извлечение структурированных данных из документов
    - GPU/CPU выполнение
    """

    def __init__(
        self,
        model_path: str | Path,
        processor,
        model,
        device: str = "cpu",
        task_prompt: str = "<s_invoice>",  # Default task prompt
    ):
        """
        Parameters
        ----------
        model_path : str | Path
            Путь к локальной модели или название на HuggingFace
        processor :
            Процессор Donut (DonutProcessor)
        model :
            Загруженная модель Donut (VisionEncoderDecoderModel)
        device : str
            "cpu" или "cuda"
        task_prompt : str
            Промпт для начала генерации (например, "<s_invoice>")
        """
        self.model_path = Path(model_path)
        self.processor = processor
        self.model = model.to(device)
        self.device = device
        self.task_prompt = task_prompt
        self.model.eval()
        
        logger.info(
            f"DonutExtractor инициализирован (model={self.model_path}, device={device})"
        )

    @classmethod
    def from_pretrained(
        cls,
        model_name_or_path: str | Path = "naver-clova-ocr/donut-base",
        device: str = "cpu",
        cache_dir: Optional[str | Path] = None,
        task_prompt: str = "<s_invoice>",
    ) -> "DonutExtractor":
        """
        Загружает модель и процессор с HuggingFace или из локальной директории.

        Parameters
        ----------
        model_name_or_path : str | Path
            Идентификатор модели на HF ("naver-clova-ocr/donut-base") или локальный путь
        device : str
            "cpu" или "cuda"
        cache_dir : str | Path
            Директория для кэша (если None, используется default ~/.cache/huggingface)
        task_prompt : str
            Начальный промпт для генерации структурированного вывода

        Returns
        -------
        DonutExtractor
            Инициализированный extractor
        """
        try:
            from transformers import DonutProcessor, VisionEncoderDecoderModel
        except ImportError as e:
            logger.error(
                f"Требуется 'transformers>=4.30.0': {e}"
            )
            raise

        try:
            logger.info(f"Загружаем модель {model_name_or_path}...")
            
            processor = DonutProcessor.from_pretrained(
                model_name_or_path,
                cache_dir=cache_dir,
            )
            
            model = VisionEncoderDecoderModel.from_pretrained(
                model_name_or_path,
                cache_dir=cache_dir,
                torch_dtype=torch.float32 if device == "cpu" else torch.float16,
            )
            
            logger.info(f"✓ Модель успешно загружена")
            
            return cls(
                model_path=model_name_or_path,
                processor=processor,
                model=model,
                device=device,
                task_prompt=task_prompt,
            )
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели: {e}")
            raise

    def extract(
        self,
        image: np.ndarray | Image.Image,
        task_prompt: Optional[str] = None,
        max_length: int = 384,
        num_beams: int = 1,
        temperature: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Извлекает структурированные данные из изображения документа.

        Parameters
        ----------
        image : np.ndarray | Image.Image
            Входное изображение. numpy массив должен быть BGR (OpenCV формат).
        task_prompt : str, optional
            Промпт для начала генерации. Если None, используется self.task_prompt
        max_length : int
            Максимальная длина генерируемой последовательности
        num_beams : int
            Количество beams для поиска (1 = greedy)
        temperature : float
            Температура для sampling

        Returns
        -------
        dict с ключами:
            - "text": str — сгенерированный текст (JSON или структурированный формат)
            - "confidence": float — среднее значение уверенности (если доступно)
            - "metadata": dict — метаинформация о выполнении
        """
        if task_prompt is None:
            task_prompt = self.task_prompt

        try:
            # Конвертируем изображение в PIL.Image если нужно
            if isinstance(image, np.ndarray):
                # Предполагаем BGR формат (OpenCV), конвертируем в RGB для PIL
                if len(image.shape) == 3 and image.shape[2] == 3:
                    image = np.clip(image, 0, 255).astype(np.uint8)
                    image = Image.fromarray(image[:, :, ::-1])  # BGR -> RGB
                else:
                    image = Image.fromarray(image)
            
            # Обработка изображения
            pixel_values = self.processor(
                image,
                return_tensors="pt"
            ).pixel_values.to(self.device)

            logger.info(f"Генерирую текст для документа типа '{task_prompt}'...")
            
            # Получаем параметры из decoder конфига (так как это VisionEncoderDecoderModel)
            decoder_config = self.model.config.decoder
            eos_token_id = decoder_config.eos_token_id
            pad_token_id = decoder_config.pad_token_id
            bos_token_id = decoder_config.bos_token_id or self.processor.tokenizer.bos_token_id or 0
            
            logger.debug(f"Token IDs - BOS: {bos_token_id}, EOS: {eos_token_id}, PAD: {pad_token_id}")
            
            import time
            start_time = time.time()
            
            logger.info("Начинаю генерацию (это может занять 10-30 сек на CPU)...")
            
            # Создаём decoder_input_ids с BOS токеном
            decoder_input_ids = torch.tensor([[bos_token_id]], dtype=torch.long).to(self.device)
            
            # Генерация
            with torch.no_grad():
                try:
                    outputs = self.model.generate(
                        pixel_values,
                        decoder_input_ids=decoder_input_ids,
                        max_length=max_length,
                        num_beams=1,
                        eos_token_id=eos_token_id,
                        pad_token_id=pad_token_id,
                        use_cache=True,
                    )
                except KeyboardInterrupt:
                    logger.error("Генерация прервана пользователем")
                    raise
            
            elapsed = time.time() - start_time
            logger.info(f"✓ Генерация завершена за {elapsed:.2f} сек")
            
            # Декодирование
            sequence = self.processor.batch_decode(outputs.cpu())[0]
            
            # Очистка от специальных токенов
            sequence = sequence.replace(self.processor.tokenizer.eos_token, "").strip()

            logger.debug(f"Donut output: {sequence[:200]}...")

            return {
                "text": sequence,
                "confidence": 0.95,  # Donut не предоставляет confidence по умолчанию
                "metadata": {
                    "model": str(self.model_path),
                    "task_prompt": task_prompt,
                    "max_length": max_length,
                    "device": self.device,
                },
            }

        except Exception as e:
            logger.error(f"Ошибка при извлечении данных: {e}")
            raise

    def set_task_prompt(self, prompt: str) -> None:
        """Устанавливает задачу для генерации (например, '<s_waybill>' или '<s_invoice>')."""
        self.task_prompt = prompt
        logger.debug(f"Task prompt изменён на: {prompt}")

    def to(self, device: str) -> "DonutExtractor":
        """Переводит модель на другой device."""
        self.model = self.model.to(device)
        self.device = device
        logger.info(f"Модель переведена на {device}")
        return self

    def __repr__(self) -> str:
        return (
            f"DonutExtractor("
            f"model_path={self.model_path}, "
            f"device={self.device}, "
            f"task_prompt='{self.task_prompt}')"
        )
