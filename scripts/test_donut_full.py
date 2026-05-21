#!/usr/bin/env python3
"""
Полный тест генерации с max_length=768
"""
import torch
import sys
import time

print("Загружаю...")
from transformers import DonutProcessor, VisionEncoderDecoderModel
from PIL import Image

MODEL_PATH = "./models/donut-base"
processor = DonutProcessor.from_pretrained(MODEL_PATH)
model = VisionEncoderDecoderModel.from_pretrained(MODEL_PATH, low_cpu_mem_usage=True)
model.eval()

print("✓ Модель загружена\n")

# Тестовое изображение
img = Image.new('RGB', (800, 600), color='white')
pixel_values = processor(img, return_tensors='pt').pixel_values

# Параметры генерации
decoder_config = model.config.decoder
bos_token_id = decoder_config.bos_token_id or 0
eos_token_id = decoder_config.eos_token_id
pad_token_id = decoder_config.pad_token_id

decoder_input_ids = torch.tensor([[bos_token_id]], dtype=torch.long)

print("Генерация с max_length=768...")
start = time.time()

try:
    with torch.no_grad():
        outputs = model.generate(
            pixel_values,
            decoder_input_ids=decoder_input_ids,
            max_length=768,
            num_beams=1,
            eos_token_id=eos_token_id,
            pad_token_id=pad_token_id,
        )
    
    elapsed = time.time() - start
    print(f"✓ Generate завершён за {elapsed:.2f}s!")
    print(f"  Output shape: {outputs.shape}")
    print(f"  Tokens: {outputs[0][:20]}... (первые 20)")
    
    # Декодирование
    sequence = processor.batch_decode(outputs.cpu())[0]
    print(f"\n✓ Декодированный результат ({len(sequence)} символов):")
    print(f"  {sequence[:300]}")
    if len(sequence) > 300:
        print(f"  ...")
    
except Exception as e:
    print(f"✗ Ошибка: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✓ ПОЛНЫЙ ТЕСТ УСПЕШЕН!")
