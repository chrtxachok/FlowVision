"""Smoke-test Donut на одном изображении."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, required=True)
    parser.add_argument("--model", type=Path, default=ROOT / "models" / "donut-trained-final")
    parser.add_argument("--device", type=str, default="cpu")
    parser.add_argument("--max-length", type=int, default=512)
    args = parser.parse_args()

    from app.ocr.donut_inference import DonutInference

    engine = DonutInference(
        model_path=args.model,
        device=args.device,
        max_length=args.max_length,
        image_width=1280,
        image_height=960,
    )
    gt_parse, sequence = engine.predict_bytes(args.path.read_bytes())
    extracted = DonutInference.to_extracted_data(gt_parse)

    print(json.dumps(
        {"sequence": sequence, "gt_parse": gt_parse, "extracted_data": extracted},
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
