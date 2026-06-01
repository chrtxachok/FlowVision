"""
Оценка Donut на датасете: field-level precision / recall / F1.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ocr.donut_format import parse_ground_truth_item  # noqa: E402
from app.ocr.donut_inference import DonutInference  # noqa: E402
sys.path.insert(0, str(ROOT / "scripts"))
from F1_metric import calculate_metrics  # noqa: E402


def load_val_records(dataset_dir: Path, split_file: Path | None) -> list[dict]:
    records = []
    for line in (dataset_dir / "metadata.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    if split_file and split_file.exists():
        val_names = {ln.strip() for ln in split_file.read_text(encoding="utf-8").splitlines() if ln.strip()}
        records = [r for r in records if r["file_name"] in val_names]
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=ROOT / "dataset" / "train")
    parser.add_argument("--model", type=Path, default=ROOT / "models" / "donut-trained-final")
    parser.add_argument("--device", type=str, default="cpu")
    parser.add_argument("--val-list", type=Path, default=None, help="Файл с именами val-изображений")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    records = load_val_records(args.dataset, args.val_list)
    if args.limit > 0:
        records = records[: args.limit]

    if not records:
        print("Нет записей для оценки")
        return 1

    engine = DonutInference(model_path=args.model, device=args.device)
    preds, gts = [], []

    for rec in records:
        img_path = args.dataset / rec["file_name"]
        if not img_path.exists():
            print(f"  [skip] {rec['file_name']}")
            continue
        from PIL import Image

        gt = parse_ground_truth_item(rec["ground_truth"])
        pred, _ = engine.predict_image(Image.open(img_path).convert("RGB"))
        preds.append(pred)
        gts.append(gt)
        print(f"  {rec['file_name']}: pred={len(pred)} fields, gt={len(gt)} fields")

    p, r, f1 = calculate_metrics(preds, gts)
    print(f"\nPrecision: {p:.4f}")
    print(f"Recall:    {r:.4f}")
    print(f"F1:        {f1:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
