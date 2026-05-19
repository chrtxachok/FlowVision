#!/usr/bin/env python3
"""
Минимальный тест генерации с максимальной отладкой
"""
import torch
import sys

print("Загружаю...")
from transformers import DonutProcessor, VisionEncoderDecoderModel
from PIL import Image

MODEL_PATH = "./models/donut-base"
processor = DonutProcessor.from_pretrained(MODEL_PATH)
model = VisionEncoderDecoderModel.from_pretrained(MODEL_PATH, low_cpu_mem_usage=True)
model.eval()

print("✓ Модель загружена")

# Тестовое изображение
img = Image.new('RGB', (800, 600), color='white')
pixel_values = processor(img, return_tensors='pt').pixel_values

print(f"Pixel values shape: {pixel_values.shape}")
print(f"Pixel values dtype: {pixel_values.dtype}")
print(f"Pixel values min/max: {pixel_values.min():.4f} / {pixel_values.max():.4f}")

# Параметры генерации
decoder_config = model.config.decoder
bos_token_id = decoder_config.bos_token_id or 0
eos_token_id = decoder_config.eos_token_id
pad_token_id = decoder_config.pad_token_id

print(f"\nПараметры:")
print(f"  BOS: {bos_token_id}, EOS: {eos_token_id}, PAD: {pad_token_id}")

# Decoder input
decoder_input_ids = torch.tensor([[bos_token_id]], dtype=torch.long)
print(f"  Decoder input: {decoder_input_ids.shape}, values: {decoder_input_ids}")

print("\nПроверяю модель:")
print(f"  device: {next(model.parameters()).device}")
print(f"  dtype: {next(model.parameters()).dtype}")

# Попробуем вызвать forward pass напрямую
print("\nТестирую forward pass...")
try:
    with torch.no_grad():
        # Encoder pass
        print("  Encoder...")
        encoder_outputs = model.encoder(pixel_values)
        print(f"    ✓ Encoder output shape: {encoder_outputs.last_hidden_state.shape}")
        
        # Decoder pass
        print("  Decoder...")
        decoder_outputs = model.decoder(
            input_ids=decoder_input_ids,
            encoder_hidden_states=encoder_outputs.last_hidden_state,
        )
        print(f"    ✓ Decoder output shape: {decoder_outputs.last_hidden_state.shape}")
        
except Exception as e:
    print(f"  ✗ Ошибка: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nТестирую generate() с очень короткой длиной...")
try:
    with torch.no_grad():
        print("  Вызываю generate(max_length=10)...")
        outputs = model.generate(
            pixel_values,
            decoder_input_ids=decoder_input_ids,
            max_length=10,  # ОЧЕНЬ короткая максимум
            num_beams=1,
            eos_token_id=eos_token_id,
            pad_token_id=pad_token_id,
        )
        print(f"  ✓ Generate завершён!")
        print(f"    Output shape: {outputs.shape}")
        print(f"    Tokens: {outputs[0]}")
        
        # Декодирование
        sequence = processor.batch_decode(outputs.cpu())[0]
        print(f"    Decoded: {sequence}")
        
except Exception as e:
    print(f"  ✗ Ошибка: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✓ ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
