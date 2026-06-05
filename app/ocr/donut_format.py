"""
Формат данных Donut для накладных (ТТН).

Соглашение:
  - task-токен: <s_waybill>
  - поле: <s_{field_name}>{value}</s_{field_name}>
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from PIL import Image

TASK_TOKEN = "<s_waybill>"
TASK_END_TOKEN = "</s_waybill>"


def task_token_id(tokenizer) -> int:
    return int(tokenizer.convert_tokens_to_ids(TASK_TOKEN))


def task_end_token_id(tokenizer) -> int:
    end_id = tokenizer.convert_tokens_to_ids(TASK_END_TOKEN)
    if end_id == tokenizer.unk_token_id:
        return int(tokenizer.eos_token_id)
    return int(end_id)


def configure_model_special_tokens(model, processor) -> None:
    """decoder_start / eos согласованы с target_sequence и generate()."""
    tokenizer = processor.tokenizer
    start_id = task_token_id(tokenizer)
    end_id = task_end_token_id(tokenizer)

    model.config.decoder_start_token_id = start_id
    model.config.eos_token_id = end_id
    model.config.pad_token_id = tokenizer.pad_token_id

    if getattr(model.config, "decoder", None) is not None:
        model.config.decoder.decoder_start_token_id = start_id
        model.config.decoder.eos_token_id = end_id
        model.config.decoder.pad_token_id = tokenizer.pad_token_id


def mask_leading_task_token_in_labels(labels, input_ids, tokenizer) -> None:
    """
    Не учим предсказывать <s_waybill>: на инференсе он уже в decoder_input_ids.
    """
    start_id = task_token_id(tokenizer)
    non_pad = (input_ids != tokenizer.pad_token_id).nonzero(as_tuple=True)[0]
    if non_pad.numel() and input_ids[non_pad[0]].item() == start_id:
        labels[non_pad[0]] = -100


def decode_token_ids(tokenizer, token_ids) -> str:
    """Без лишних пробелов между спец-токенами (batch_decode их вставляет)."""
    if hasattr(token_ids, "tolist"):
        token_ids = token_ids.tolist()
    return tokenizer.decode(
        token_ids,
        skip_special_tokens=False,
        clean_up_tokenization_spaces=False,
    )


def clean_generated_sequence(sequence: str, tokenizer) -> str:
    text = sequence.replace(tokenizer.eos_token or "", "")
    text = text.replace(tokenizer.pad_token or "", "")
    end_id = task_end_token_id(tokenizer)
    end_token = tokenizer.convert_ids_to_tokens(end_id)
    if end_token and end_token not in (tokenizer.unk_token, None):
        text = text.replace(end_token, "")
    return text.strip()

# Все поля датасета (порядок фиксирован для стабильной генерации)
FIELD_NAMES: List[str] = [
    "waybill_number",
    "document_date",
    "sender_name",
    "recipient_name",
    "product_name",
    "carrier_name",
    "sender_inn",
    "recipient_inn",
    "sender_kpp",
    "recipient_kpp",
    "contract_number",
    "invoice_number",
    "carrier_inn",
    "driver_name",
    "vehicle_number",
    "total_amount",
    "arrival_time",
    "departure_time",
    "loading_address",
    "unloading_address",
]


def field_open_token(name: str) -> str:
    return f"<s_{name}>"


def field_close_token(name: str) -> str:
    return f"</s_{name}>"


def field_bbox_open_token(name: str) -> str:
    return f"<s_{name}_bbox>"


def field_bbox_close_token(name: str) -> str:
    return f"</s_{name}_bbox>"


def build_special_tokens() -> List[str]:
    """Список токенов для добавления в tokenizer."""
    tokens = [TASK_TOKEN, TASK_END_TOKEN]
    for name in FIELD_NAMES:
        tokens.append(field_open_token(name))
        tokens.append(field_close_token(name))
        tokens.append(field_bbox_open_token(name))
        tokens.append(field_bbox_close_token(name))
    return tokens


def gt_parse_to_sequence(
    gt_parse: Dict[str, Any],
    bboxes: dict[str, list[float]] | None = None,
    sort_keys: bool = True,
) -> str:
    """Преобразует словарь полей и bbox в целевую последовательность Donut."""
    items = gt_parse.items()
    if sort_keys:
        items = sorted(items, key=lambda x: x[0])

    parts = [TASK_TOKEN]
    for key, value in items:
        if value is None:
            continue
        text = str(value).strip()
        if not text:
            continue
        parts.append(f"{field_open_token(key)}{text}{field_close_token(key)}")

        if bboxes is not None:
            bbox = bboxes.get(key)
            if bbox and len(bbox) == 4:
                try:
                    bbox_text = ",".join(format(float(v), ".4f") for v in bbox)
                except (TypeError, ValueError):
                    bbox_text = ",".join(str(v) for v in bbox)
                parts.append(
                    f"{field_bbox_open_token(key)}{bbox_text}{field_bbox_close_token(key)}"
                )

    parts.append(TASK_END_TOKEN)
    return "".join(parts)


def parse_ground_truth_item(ground_truth: str) -> Dict[str, Any]:
    """Парсит ground_truth из jsonl (JSON-строка с gt_parse)."""
    data = json.loads(ground_truth)
    if "gt_parse" in data:
        return data["gt_parse"]
    return data


def sequence_to_gt_parse(sequence: str) -> Dict[str, str]:
    """Извлекает поля из сгенерированной моделью последовательности."""
    result: Dict[str, str] = {}
    for name in FIELD_NAMES:
        pattern = re.compile(
            re.escape(field_open_token(name)) + r"(.*?)" + re.escape(field_close_token(name)),
            re.DOTALL,
        )
        match = pattern.search(sequence)
        if match:
            value = match.group(1).strip()
            if value:
                result[name] = value
    return result


def resize_image_keep_aspect(image: Image.Image, max_width: int, max_height: int) -> Image.Image:
    w, h = image.size
    scale = min(max_width / w, max_height / h, 1.0)
    if scale >= 1.0:
        return image
    return image.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)


def apply_processor_image_size(processor, height: int, width: int) -> None:
    size = {"height": height, "width": width}
    if hasattr(processor, "image_processor") and processor.image_processor is not None:
        processor.image_processor.size = size
    elif hasattr(processor, "feature_extractor") and processor.feature_extractor is not None:
        processor.feature_extractor.size = size


def document_id_from_filename(filename: str) -> str:
    """ТТН_0008_page-0001.jpg -> ТТН_0008"""
    stem = filename.rsplit(".", 1)[0]
    if "_page-" in stem:
        return stem.split("_page-")[0]
    return stem
