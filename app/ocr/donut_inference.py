"""
Инференс дообученной модели Donut для накладных.
"""
from __future__ import annotations

import logging
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
import torch
from PIL import Image
from transformers import DonutProcessor, VisionEncoderDecoderModel

from app.ocr.donut_format import (
    TASK_TOKEN,
    apply_processor_image_size,
    build_special_tokens,
    clean_generated_sequence,
    configure_model_special_tokens,
    decode_token_ids,
    resize_image_keep_aspect,
    sequence_to_gt_parse,
    task_end_token_id,
)

logger = logging.getLogger(__name__)

# Маппинг полей Donut → API (WaybillProcessor)
API_FIELD_MAP = {
    "waybill_number": "waybill_number",
    "document_date": "date",
    "sender_name": "sender",
    "recipient_name": "recipient",
    "product_name": "cargo_description",
    "total_amount": "total_amount",
    "driver_name": "driver_name",
    "vehicle_number": "vehicle_number",
    "sender_inn": "sender_inn",
    "recipient_inn": "recipient_inn",
    "carrier_name": "carrier_name",
    "carrier_inn": "carrier_inn",
    "loading_address": "loading_address",
    "unloading_address": "unloading_address",
    "arrival_time": "arrival_time",
    "departure_time": "departure_time",
    "contract_number": "contract_number",
    "invoice_number": "invoice_number",
}


class DonutInference:
    """Загрузка и запуск Donut на одном изображении."""

    def __init__(
        self,
        model_path: Path,
        device: str = "cpu",
        max_length: int = 768,
        image_width: int = 1280,
        image_height: int = 960,
        num_beams: int = 4,
        repetition_penalty: float = 1.15,
    ):
        self.model_path = Path(model_path)
        self.device = device if device == "cuda" and torch.cuda.is_available() else "cpu"
        self.max_length = max_length
        self.image_width = image_width
        self.image_height = image_height
        self.num_beams = num_beams
        self.repetition_penalty = repetition_penalty
        self.processor: Optional[DonutProcessor] = None
        self.model: Optional[VisionEncoderDecoderModel] = None
        self._load()

    def _load(self) -> None:
        if self.model_path.exists():
            self._load_from_export()
            return

        fallback_path = self.model_path.parent / "donut-trained"
        checkpoint_files = []
        if fallback_path.exists():
            checkpoint_files = sorted(fallback_path.glob("*.ckpt"))
        if checkpoint_files:
            self._load_from_checkpoint(fallback_path, checkpoint_files[0])
            return

        raise FileNotFoundError(
            f"Модель Donut не найдена: {self.model_path}\n"
            "Обучите: python train/train.py\n"
            "Или распакуйте `donut-trained-final.zip` в models/donut-trained-final/"
        )

    def _load_from_export(self) -> None:
        logger.info("Загрузка Donut из %s (device=%s)", self.model_path, self.device)
        self.processor = DonutProcessor.from_pretrained(self.model_path)
        # Colab/lowmem обучали на 1280x960; в processor_config часто остаётся 1920x2560
        if self.image_width > 0 and self.image_height > 0:
            apply_processor_image_size(self.processor, self.image_height, self.image_width)
        self.model = VisionEncoderDecoderModel.from_pretrained(self.model_path)
        configure_model_special_tokens(self.model, self.processor)
        self.model.to(self.device)
        self.model.eval()

        self.eos_token_id = task_end_token_id(self.processor.tokenizer)
        self.decoder_start_token_id = self.model.config.decoder_start_token_id
        self.task_token = self._resolve_task_token()

    def _load_from_checkpoint(self, checkpoint_dir: Path, checkpoint_file: Path) -> None:
        base_model_dir = checkpoint_dir.parent / "donut-base"
        if not base_model_dir.exists():
            raise FileNotFoundError(
                f"Base Donut model not found for checkpoint fallback: {base_model_dir}\n"
                "Скачайте: python scripts/download_model.py"
            )

        logger.warning(
            "Модель Donut не найдена: %s. Загружаем checkpoint из %s и строим модель из %s",
            self.model_path,
            checkpoint_file,
            base_model_dir,
        )

        self.processor = DonutProcessor.from_pretrained(base_model_dir)
        special_tokens = build_special_tokens()
        self.processor.tokenizer.add_special_tokens({"additional_special_tokens": special_tokens})

        if self.image_width > 0 and self.image_height > 0:
            apply_processor_image_size(self.processor, self.image_height, self.image_width)

        self.model = VisionEncoderDecoderModel.from_pretrained(base_model_dir)
        self.model.decoder.resize_token_embeddings(len(self.processor.tokenizer))
        configure_model_special_tokens(self.model, self.processor)

        try:
            checkpoint = torch.load(checkpoint_file, map_location="cpu", weights_only=False)
        except TypeError:
            checkpoint = torch.load(checkpoint_file, map_location="cpu")
        state_dict = checkpoint.get("state_dict", checkpoint)
        cleaned_state_dict = {
            key[len("model.") :] if key.startswith("model.") else key: value
            for key, value in state_dict.items()
        }

        missing, unexpected = self.model.load_state_dict(cleaned_state_dict, strict=False)
        if missing:
            logger.warning("Недостающие ключи при загрузке checkpoint: %s", missing)
        if unexpected:
            logger.warning("Лишние ключи в checkpoint: %s", unexpected)

        self.model.to(self.device)
        self.model.eval()

        self.eos_token_id = task_end_token_id(self.processor.tokenizer)
        self.decoder_start_token_id = self.model.config.decoder_start_token_id
        self.task_token = self._resolve_task_token()

    def _resolve_task_token(self) -> str:
        assert self.processor is not None
        tokenizer = self.processor.tokenizer
        candidates = [TASK_TOKEN, "<s_ttn>", "<s_doc>"]
        for candidate in candidates:
            token_id = tokenizer.convert_tokens_to_ids(candidate)
            if token_id != tokenizer.unk_token_id:
                logger.info("Используется task token %s (id=%s)", candidate, token_id)
                return candidate

        if self.decoder_start_token_id is not None:
            token = tokenizer.convert_ids_to_tokens(self.decoder_start_token_id)
            if token not in (tokenizer.unk_token, None):
                logger.info(
                    "Используется decoder_start_token_id %s (token=%s)",
                    self.decoder_start_token_id,
                    token,
                )
                return token

        raise ValueError(
            "Не найден task token для Donut. Проверьте модель и tokenizer в %s" % self.model_path
        )

    @classmethod
    def from_settings(cls) -> "DonutInference":
        from app.config import settings

        return cls(
            model_path=settings.DONUT_MODEL_PATH,
            device=settings.DONUT_DEVICE,
            max_length=settings.DONUT_MAX_LENGTH,
            image_width=settings.DONUT_IMAGE_WIDTH,
            image_height=settings.DONUT_IMAGE_HEIGHT,
            num_beams=settings.DONUT_NUM_BEAMS,
            repetition_penalty=settings.DONUT_REPETITION_PENALTY,
        )

    def _image_from_bytes(self, file_bytes: bytes) -> Image.Image:
        return Image.open(BytesIO(file_bytes)).convert("RGB")

    def _image_from_numpy(self, image: np.ndarray) -> Image.Image:
        import cv2

        if len(image.shape) == 3 and image.shape[2] == 3:
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        else:
            rgb = image
        return Image.fromarray(rgb)

    @torch.inference_mode()
    def predict_image(self, image: Image.Image) -> Tuple[Dict[str, str], str]:
        assert self.processor is not None and self.model is not None

        if self.image_width > 0 and self.image_height > 0:
            image = resize_image_keep_aspect(image, self.image_width, self.image_height)
        pixel_values = self.processor(image, return_tensors="pt").pixel_values
        pixel_values = pixel_values.to(self.device)

        decoder_input_ids = self.processor.tokenizer(
            self.task_token,
            add_special_tokens=False,
            return_tensors="pt",
        ).input_ids.to(self.device)

        if decoder_input_ids.numel() == 0 or decoder_input_ids[0, 0].item() == self.processor.tokenizer.unk_token_id:
            if self.decoder_start_token_id is not None:
                decoder_input_ids = torch.tensor(
                    [[self.decoder_start_token_id]],
                    dtype=torch.long,
                    device=self.device,
                )
                logger.warning(
                    "Не удалось получить decoder_input_ids из task token, используем decoder_start_token_id=%s",
                    self.decoder_start_token_id,
                )

        outputs = self.model.generate(
            pixel_values,
            decoder_input_ids=decoder_input_ids,
            max_new_tokens=self.max_length,
            pad_token_id=self.processor.tokenizer.pad_token_id,
            eos_token_id=self.eos_token_id,
            use_cache=True,
            num_beams=self.num_beams,
            repetition_penalty=self.repetition_penalty,
            no_repeat_ngram_size=3,
            early_stopping=True,
        )

        sequence = clean_generated_sequence(
            decode_token_ids(self.processor.tokenizer, outputs[0]),
            self.processor.tokenizer,
        )
        gt_parse = sequence_to_gt_parse(sequence)
        return gt_parse, sequence

    def predict_bytes(self, file_bytes: bytes) -> Tuple[Dict[str, str], str]:
        return self.predict_image(self._image_from_bytes(file_bytes))

    def predict_numpy(self, image: np.ndarray) -> Tuple[Dict[str, str], str]:
        return self.predict_image(self._image_from_numpy(image))

    @staticmethod
    def to_extracted_data(gt_parse: Dict[str, str], default_confidence: float = 0.85) -> Dict[str, Any]:
        """Преобразует gt_parse в формат extracted_data API."""
        extracted: Dict[str, Any] = {}
        for src_key, value in gt_parse.items():
            api_key = API_FIELD_MAP.get(src_key, src_key)
            extracted[api_key] = {
                "value": value,
                "confidence": default_confidence,
                "raw_text": value,
            }
        return extracted

    @staticmethod
    def average_confidence(extracted_data: Dict[str, Any]) -> float:
        confs = [
            f.get("confidence", 0.0)
            for f in extracted_data.values()
            if isinstance(f, dict) and f.get("value")
        ]
        return round(sum(confs) / len(confs), 4) if confs else 0.0
