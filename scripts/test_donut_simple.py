#!/usr/bin/env python3
"""
Простой тест - проверяем может ли модель вообще работать
"""
import os
import torch


print("Информация о системе:")
print(f"  PyTorch version: {torch.__version__}")
print(f"  CUDA available: {torch.cuda.is_available()}")
print(f"  CPU memory: проверка...")

try:
    import psutil
    import os
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    print(f"  Current memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")
except:
    pass

print("\n" + "="*60)
print("Пытаюсь загрузить модель Donut...")
print("="*60)

try:
    from transformers import DonutProcessor, VisionEncoderDecoderModel
    
    MODEL_PATH = "./models/donut-base"
    
    print(f"\nЗагружаю processor из {MODEL_PATH}...")
    processor = DonutProcessor.from_pretrained(MODEL_PATH, trust_remote_code=True)
    print("✓ Processor загружен")
    
    print(f"\nЗагружаю модель...")
    model = VisionEncoderDecoderModel.from_pretrained(
        MODEL_PATH,
        trust_remote_code=True,
        torch_dtype=torch.float32,
        low_cpu_mem_usage=True,  # ← ВАЖНО для CPU
    )
    print("✓ Модель загружена")
    
    print(f"\nПереводу модель в eval mode...")
    model.eval()
    print("✓ Model в eval mode")
    
    print(f"\nПроверяю конфиг модели:")
    print(f"  model.config type: {type(model.config).__name__}")
    print(f"  model.config decoder: {model.config.decoder}")
    
    # Для VisionEncoderDecoderModel нужно использовать decoder конфиг
    decoder_config = model.config.decoder
    print(f"  decoder.eos_token_id: {decoder_config.eos_token_id}")
    print(f"  decoder.pad_token_id: {decoder_config.pad_token_id}")
    print(f"  decoder.bos_token_id: {decoder_config.bos_token_id}")
    
    print(f"\nПроверяю токенизер:")
    print(f"  bos_token_id: {processor.tokenizer.bos_token_id}")
    print(f"  eos_token_id: {processor.tokenizer.eos_token_id}")
    print(f"  pad_token_id: {processor.tokenizer.pad_token_id}")
    
    print("\n✓ Модель успешно загружена и готова к работе!")
    
except Exception as e:
    print(f"\n✗ Ошибка: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
