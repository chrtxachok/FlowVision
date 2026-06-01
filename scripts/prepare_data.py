#!/usr/bin/env python3
"""
Конвертация экспорта Label Studio в формат Donut (metadata.jsonl + копирование изображений).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ocr.donut_format import gt_parse_to_sequence, parse_ground_truth_item  # noqa: E402


def _extract_fields_from_ls_entry(entry: dict) -> tuple[dict[str, str], dict[str, list[float]]]:
    """
    Извлечение полей из Label Studio для новой разметки.
    Структура: rectanglelabels (поле) + textarea (значение) связаны по id.
    """
    if not entry.get("annotations"):
        return {}, {}
    
    results = entry["annotations"][0].get("result", [])
    
    # Сопоставление по id: rectanglelabels (ключи) с textarea (значения)
    by_id: dict[str, dict] = {}
    for res in results:
        res_id = res.get("id")
        res_type = res.get("type")
        
        if res_id not in by_id:
            by_id[res_id] = {}
        
        value = res.get("value", {})
        
        if res_type == "rectanglelabels":
            labels = value.get("rectanglelabels", [])
            if labels:
                by_id[res_id]["key"] = labels[0]
            x = value.get("x")
            y = value.get("y")
            width = value.get("width")
            height = value.get("height")
            if x is not None and y is not None and width is not None and height is not None:
                by_id[res_id]["bbox"] = [x, y, width, height]
        elif res_type == "textarea":
            text_val = value.get("text", [])
            if text_val:
                by_id[res_id]["value"] = text_val[0] if isinstance(text_val, list) else text_val
    
    # Собрать финальный результат
    final_parse: dict[str, str] = {}
    bboxes: dict[str, list[float]] = {}
    for data in by_id.values():
        key = data.get("key")
        val = data.get("value")
        if key and val:
            final_parse[key] = str(val).strip()
            if "bbox" in data:
                bboxes[key] = data["bbox"]
    
    return final_parse, bboxes


def convert_to_donut_format(
    input_json_path: Path,
    output_dir: Path,
    images_source_dir: Path,
) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_jsonl = output_dir / "metadata.jsonl"

    with open(input_json_path, "r", encoding="utf-8") as f:
        ls_data = json.load(f)

    written = 0
    skipped = 0
    with open(output_jsonl, "w", encoding="utf-8") as f_out:
        for entry in ls_data:
            # Label Studio file_upload может содержать UUID префикс
            raw_filename = entry["file_upload"]
            # Пробуем найти файл по разным вариантам
            possible_names = [raw_filename]
            
            # Если есть UUID префикс (uuid-filename), добавляем чистое имя
            if "-" in raw_filename and len(raw_filename) > 36:  # UUID примерно 36 символов
                clean_name = raw_filename.split("-", 1)[-1]
                possible_names.append(clean_name)
            
            gt_parse, bboxes = _extract_fields_from_ls_entry(entry)
            if not gt_parse:
                skipped += 1
                continue

            ground_truth = json.dumps({"gt_parse": gt_parse}, ensure_ascii=False)
            target_sequence = gt_parse_to_sequence(gt_parse, bboxes=bboxes)

            # Ищем изображение
            src_image = None
            for name_variant in possible_names:
                candidate = images_source_dir / name_variant
                if candidate.exists():
                    src_image = candidate
                    break
            
            # Если не нашли - ищем по регистронезависимому поиску
            if not src_image:
                for name_variant in possible_names:
                    candidates = [p for p in images_source_dir.iterdir() if p.name.lower() == name_variant.lower()]
                    if candidates:
                        src_image = candidates[0]
                        break
            
            if not src_image:
                print(f"  [skip] нет изображения: {raw_filename}")
                skipped += 1
                continue

            # Используем чистое имя для выходного файла
            clean_filename = raw_filename.split("-", 1)[-1] if "-" in raw_filename else raw_filename
            dst_image = output_dir / clean_filename
            
            if not dst_image.exists() or dst_image.stat().st_mtime < src_image.stat().st_mtime:
                shutil.copy2(src_image, dst_image)

            jsonl_line = {
                "file_name": clean_filename,
                "ground_truth": ground_truth,
                "target_sequence": target_sequence,
            }
            f_out.write(json.dumps(jsonl_line, ensure_ascii=False) + "\n")
            written += 1

    print(f"Готово: {written} записей, {skipped} пропущено")
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Label Studio → Donut dataset")
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "dataset" / "raw" / "train1.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "dataset" / "train",
    )
    parser.add_argument(
        "--images",
        type=Path,
        default=ROOT / "dataset" / "annotated",
    )
    args = parser.parse_args()

    if not args.input.exists():
        print(f"Ошибка: не найден {args.input}")
        return 1
    if not args.images.exists():
        print(f"Ошибка: не найдена папка с изображениями {args.images}")
        return 1

    count = convert_to_donut_format(args.input, args.output_dir, args.images)
    print(f"Готово: {count} записей -> {args.output_dir / 'metadata.jsonl'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
