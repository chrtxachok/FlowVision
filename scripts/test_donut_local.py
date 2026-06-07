#!/usr/bin/env python3
"""
Локальный тест модели Donut без HTTP
"""
import sys
import time
import os


# Отключаем прокси
os.environ['no_proxy'] = '*'
os.environ.pop('HTTP_PROXY', None)
os.environ.pop('HTTPS_PROXY', None)

from PIL import Image
import numpy as np

print("=" * 60)
print("ТЕСТ МОДЕЛИ DONUT (локально)")
print("=" * 60)

# 1. Загружаем модель
print("\n1️⃣ Загружаю модель...")
try:
    from transformers import DonutProcessor, VisionEncoderDecoderModel
    import torch
    
    MODEL_PATH = "./models/donut-base"
    DEVICE = "cpu"
    
    print(f"   Путь: {MODEL_PATH}")
    print(f"   Device: {DEVICE}")
    
    start = time.time()
    processor = DonutProcessor.from_pretrained(MODEL_PATH)
    model = VisionEncoderDecoderModel.from_pretrained(MODEL_PATH)
    model = model.to(DEVICE)
    model.eval()
    elapsed = time.time() - start
    print(f"   ✓ Модель загружена за {elapsed:.2f}s")
    
except Exception as e:
    print(f"   ✗ Ошибка загрузки: {e}")
    sys.exit(1)

# 2. Создаём тестовое изображение
print("\n2️⃣ Создаю тестовое изображение...")
try:
    # Создаём белое изображение с текстом
    img = Image.new('RGB', (800, 600), color='white')
    
    # Если есть пример документа, используем его
    example_paths = [
        "./static/example.jpg",
        "./static/document.jpg",
        "./static/waybill.jpg",
    ]
    
    for path in example_paths:
        if os.path.exists(path):
            print(f"   Используется пример: {path}")
            img = Image.open(path).convert('RGB')
            break
    else:
        print(f"   Используется пустое изображение (800x600)")
    
    print(f"   Размер: {img.size}")
    
except Exception as e:
    print(f"   ✗ Ошибка создания изображения: {e}")
    sys.exit(1)

# 3. Обработка изображения
print("\n3️⃣ Обрабатываю изображение...")
try:
    start = time.time()
    pixel_values = processor(img, return_tensors="pt").pixel_values
    pixel_values = pixel_values.to(DEVICE)
    elapsed = time.time() - start
    print(f"   ✓ Обработано за {elapsed:.2f}s")
    print(f"   Shape: {pixel_values.shape}")
    
except Exception as e:
    print(f"   ✗ Ошибка обработки: {e}")
    sys.exit(1)

# 4. Генерация
print("\n4️⃣ Запускаю генерацию (может занять 10-30 сек)...")
try:
    task_prompt = "<s_waybill>"
    
    start = time.time()
    
    print(f"   Task prompt: {task_prompt}")
    print(f"   Max length: 768")
    
    # Получаем параметры из decoder конфига (так как это VisionEncoderDecoderModel)
    decoder_config = model.config.decoder
    eos_token_id = decoder_config.eos_token_id
    pad_token_id = decoder_config.pad_token_id
    bos_token_id = decoder_config.bos_token_id or processor.tokenizer.bos_token_id or 0
    
    print(f"   Token IDs из decoder_config - BOS: {bos_token_id}, EOS: {eos_token_id}, PAD: {pad_token_id}")
    
    # Создаём decoder_input_ids с BOS токеном
    decoder_input_ids = torch.tensor([[bos_token_id]], dtype=torch.long).to(DEVICE)
    print(f"   Decoder input shape: {decoder_input_ids.shape}")
    print(f"   Начинаю...")
    
    with torch.no_grad():
        print("   Вызываю model.generate()...")
        try:
            outputs = model.generate(
                pixel_values,
                decoder_input_ids=decoder_input_ids,
                max_length=768,
                num_beams=1,
                eos_token_id=eos_token_id,
                pad_token_id=pad_token_id,
                use_cache=True,
            )
            print("   model.generate() завершён!")
        except RuntimeError as e:
            print(f"   ✗ RuntimeError в generate(): {e}")
            import traceback
            traceback.print_exc()
            raise
        except Exception as e:
            print(f"   ✗ Неожиданная ошибка в generate(): {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    elapsed = time.time() - start
    print(f"   ✓ Генерация завершена за {elapsed:.2f}s")
    
except Exception as e:
    print(f"   ✗ Ошибка генерации: {type(e).__name__}: {e}")
    import traceback
    print("\nПолная ошибка:")
    traceback.print_exc()
    sys.exit(1)

# 5. Декодирование
print("\n5️⃣ Декодирую результат...")
try:
    print(f"   Outputs shape: {outputs.shape}")
    print(f"   Вызываю batch_decode()...")
    sequence = processor.batch_decode(outputs.cpu())[0]
    print(f"   ✓ Результат ({len(sequence)} символов):")
    print(f"   {sequence[:500]}")
    if len(sequence) > 500:
        print(f"   ...")
    
except Exception as e:
    print(f"   ✗ Ошибка декодирования: {type(e).__name__}: {e}")
    import traceback
    print("\nПолная ошибка:")
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ ТЕСТ ЗАВЕРШЁН УСПЕШНО")
print("=" * 60)
