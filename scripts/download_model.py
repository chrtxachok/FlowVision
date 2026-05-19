import os
import sys

# Отключить все прокси переменные
for key in list(os.environ.keys()):
    if 'proxy' in key.lower():
        del os.environ[key]

os.environ['no_proxy'] = '*'

# НЕ использовать зеркало - скачивать с оригинального HuggingFace
# Убрать HF_ENDPOINT если установлен
os.environ.pop('HF_ENDPOINT', None)

from transformers import DonutProcessor, VisionEncoderDecoderModel

print("Скачивание модели donut-base с HuggingFace...")
model_name = "naver-clova-ix/donut-base"
try:
    processor = DonutProcessor.from_pretrained(model_name)
    model = VisionEncoderDecoderModel.from_pretrained(model_name)
    
    # Создать директорию если её нет
    os.makedirs("./models", exist_ok=True)
    
    # Сохраняем локально, чтобы больше не зависеть от сети
    processor.save_pretrained("./models/donut-base")
    model.save_pretrained("./models/donut-base")
    print("✓ Модель успешно скачана в папку ./models/donut-base")
except Exception as e:
    print(f"✗ Ошибка загрузки: {e}")
    print("Попробуйте установить huggingface_hub:")
    print("  pip install huggingface_hub --upgrade")
    sys.exit(1)