#!/usr/bin/env python3
"""
Тест Donut на реальном документе
"""
import sys
import torch
from pathlib import Path

print("Загружаю модель...")
from transformers import DonutProcessor, VisionEncoderDecoderModel
from PIL import Image

MODEL_PATH = "./models/donut-base"
processor = DonutProcessor.from_pretrained(MODEL_PATH)
model = VisionEncoderDecoderModel.from_pretrained(MODEL_PATH, low_cpu_mem_usage=True)
model.eval()

print("✓ Модель загружена\n")

# Ищем документ
doc_path = None
for p in Path(".").rglob("ТТН_0002_page-0002.jpg"):
    doc_path = p
    break

if not doc_path:
    print("❌ Документ ТТН_0002_page-0002.jpg не найден")
    print("Ищу другие jpg файлы...")
    jpg_files = list(Path(".").rglob("*.jpg"))
    if jpg_files:
        doc_path = jpg_files[0]
        print(f"Буду использовать: {doc_path}")
    else:
        print("❌ JPG файлы не найдены")
        sys.exit(1)

print(f"📄 Документ: {doc_path}")

# Загружаем документ
img = Image.open(doc_path).convert('RGB')
print(f"   Размер: {img.size}")

# Обработка
pixel_values = processor(img, return_tensors='pt').pixel_values
print(f"   Pixel values shape: {pixel_values.shape}\n")

# Параметры генерации
decoder_config = model.config.decoder
bos_token_id = decoder_config.bos_token_id or 0
eos_token_id = decoder_config.eos_token_id
pad_token_id = decoder_config.pad_token_id

decoder_input_ids = torch.tensor([[bos_token_id]], dtype=torch.long)

print("Тестирую разные task prompts:\n")

task_prompts = [
    "<s_waybill>",
    "<s_invoice>",
    "<s>",
    ""
]

for task_prompt in task_prompts:
    print(f"📍 Task prompt: '{task_prompt}'")
    
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
        
        sequence = processor.batch_decode(outputs.cpu())[0]
        
        print(f"   Output length: {len(sequence)} chars")
        print(f"   First 200 chars: {sequence[:200]}")
        if len(sequence) > 200:
            print(f"   Last 100 chars: ...{sequence[-100:]}")
        print()
        
    except Exception as e:
        print(f"   ✗ Ошибка: {e}\n")

print("✓ Тест завершён")
