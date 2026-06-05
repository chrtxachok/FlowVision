"""Упаковать dataset/train в zip для загрузки в Colab."""
import argparse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "dataset" / "train",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "train_dataset.zip",
    )
    args = parser.parse_args()

    if not (args.input / "metadata.jsonl").exists():
        print(f"Сначала: python scripts/prepare_data.py")
        return 1

    with zipfile.ZipFile(args.output, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in args.input.iterdir():
            if f.is_file():
                zf.write(f, arcname=f.name)

    print(f"Создан: {args.output} ({args.output.stat().st_size / 1024 / 1024:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
