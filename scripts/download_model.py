#!/usr/bin/env python3
"""Скачивание naver-clova-ix/donut-base в ./models/donut-base"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "models" / "donut-base"

# Зеркало HuggingFace (РФ)
if not os.environ.get("HF_ENDPOINT"):
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from transformers import DonutProcessor, VisionEncoderDecoderModel

model_name = "Akajackson/donut_rus"
print(f"Downloading {model_name} -> {OUT}")
OUT.mkdir(parents=True, exist_ok=True)

processor = DonutProcessor.from_pretrained(model_name)
model = VisionEncoderDecoderModel.from_pretrained(model_name)

processor.save_pretrained(OUT)
model.save_pretrained(OUT)
print(f"Модель сохранена: {OUT}")