#!/usr/bin/env python3
"""
Упаковка проекта для Google Colab (приватный репозиторий — только zip).

Создаёт два архива:
  flowvision_colab_code.zip  — код (app, train, scripts, configs, notebook)
  train_dataset.zip          — dataset/train (jpg + metadata.jsonl)

Или один общий архив: --single
"""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Папки и файлы, которые нужны в Colab
CODE_INCLUDE_DIRS = ("app", "train", "scripts", "configs", "notebooks")
CODE_INCLUDE_FILES = ("requirements.txt",)

# Не включать в архив кода
CODE_SKIP_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ipynb_checkpoints",
    "logs",
    "cache",
    ".venv",
    "venv",
    "models",
    ".git",
    ".idea",
    ".vscode",
}

DATASET_DIR = ROOT / "dataset" / "train"


def _should_skip(path: Path) -> bool:
    return any(part in CODE_SKIP_PARTS for part in path.parts)


def _add_to_zip(zf: zipfile.ZipFile, file_path: Path, arcname: str) -> None:
    zf.write(file_path, arcname=arcname)


def pack_code(output: Path) -> int:
    count = 0
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in CODE_INCLUDE_FILES:
            p = ROOT / name
            if p.exists():
                _add_to_zip(zf, p, name)
                count += 1

        for dir_name in CODE_INCLUDE_DIRS:
            base = ROOT / dir_name
            if not base.exists():
                continue
            for f in base.rglob("*"):
                if not f.is_file() or _should_skip(f):
                    continue
                arc = f.relative_to(ROOT).as_posix()
                _add_to_zip(zf, f, arc)
                count += 1

    return count


def pack_dataset(output: Path) -> int:
    if not (DATASET_DIR / "metadata.jsonl").exists():
        raise FileNotFoundError(
            f"Нет {DATASET_DIR / 'metadata.jsonl'}. Сначала: python scripts/prepare_data.py"
        )
    count = 0
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in DATASET_DIR.iterdir():
            if f.is_file():
                zf.write(f, arcname=f"dataset/train/{f.name}")
                count += 1
    return count


def pack_single(output: Path) -> None:
    import tempfile
    import shutil

    tmp_code = output.parent / "_tmp_code.zip"
    tmp_data = output.parent / "_tmp_data.zip"
    try:
        pack_code(tmp_code)
        pack_dataset(tmp_data)
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zout:
            for tmp in (tmp_code, tmp_data):
                with zipfile.ZipFile(tmp, "r") as zin:
                    for item in zin.infolist():
                        zout.writestr(item, zin.read(item.filename))
    finally:
        tmp_code.unlink(missing_ok=True)
        tmp_data.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Упаковка FlowVision для Colab")
    parser.add_argument(
        "--single",
        action="store_true",
        help="Один zip: код + датасет (flowvision_colab_all.zip)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT,
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.single:
        out = args.output_dir / "flowvision_colab_all.zip"
        pack_single(out)
        print(f"Создан: {out} ({out.stat().st_size / 1024 / 1024:.1f} MB)")
        print("В Colab: загрузите этот один файл и распакуйте в /content/FlowVision")
        return 0

    code_zip = args.output_dir / "flowvision_colab_code.zip"
    data_zip = args.output_dir / "train_dataset.zip"
    n_code = pack_code(code_zip)
    n_data = pack_dataset(data_zip)
    print(f"Код:     {code_zip} ({n_code} файлов, {code_zip.stat().st_size / 1024:.0f} KB)")
    print(f"Датасет: {data_zip} ({n_data} файлов, {data_zip.stat().st_size / 1024 / 1024:.1f} MB)")
    print("\nВ Colab загрузите ОБА zip (см. notebooks/train_donut_colab.ipynb)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
