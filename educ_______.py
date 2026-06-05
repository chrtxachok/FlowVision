#!/usr/bin/env python3
"""Запуск тестового урезанного обучения (обёртка над train/train.py --minimal)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

if __name__ == "__main__":
    cmd = [sys.executable, str(ROOT / "train" / "train.py"), "--minimal", *sys.argv[1:]]
    print("Запуск:", " ".join(cmd))
    raise SystemExit(subprocess.call(cmd))
