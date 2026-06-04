# train/train.py - ИСПРАВЛЕННАЯ ВЕРСИЯ

import json
import torch
import yaml
from pathlib import Path
from transformers import DonutProcessor, VisionEncoderDecoderModel, TrainingArguments, Trainer
from datasets import Dataset  # ← Убедитесь что установлено: pip install datasets
from PIL import Image
import numpy as np
import re

processor = None

# Загрузка конфигурации
with open("config.yaml", 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# Маппинг лейблов
LABEL_LIST = [
    "waybill_number", "document_date", "sender_name", "recipient_name",
    "total_amount", "sender_inn", "recipient_inn", "cargo_description",
    "carrier_name", "driver_name", "vehicle_number", "contract_number",
    "invoice_number", "arrival_time", "departure_time", 
    "loading_address", "unloading_address", "product_name"
]

def parse_donut_output(output_text: str) -> dict:
    """Парсит вывод Donut в словарь полей."""
    fields = {}
    pattern = r'<s_([^>]+)>([^<]+)</s_\1>'
    matches = re.findall(pattern, output_text)
    for field, value in matches:
        fields[field] = value.strip()
    return fields

def load_dataset(metadata_path: str, processor: DonutProcessor, max_length: int = 1024):
    """Загружает датасет в формате Donut."""
    
    print(f"📂 Загрузка датасета из: {metadata_path}")
    
    if not Path(metadata_path).exists():
        raise FileNotFoundError(f"Файл не найден: {metadata_path}")
    
    with open(metadata_path, 'r', encoding='utf-8') as f:
        entries = [json.loads(line) for line in f if line.strip()]
    
    print(f"✓ Загружено {len(entries)} записей")
    
    def preprocess(entry):
        # Загрузка изображения
        filename = Path(entry["file_name"]).name  # Берем только имя файла, убираем пути
        
        # Список возможных путей, где могут лежать картинки
        possible_paths = [
            Path("dataset/raw") / filename,
            Path("dataset/train/images") / filename,
            Path("dataset") / filename,
        ]
        
        image_path = None
        for p in possible_paths:
            if p.exists():
                image_path = p
                break
        
        if image_path is None:
            # Если картинка не найдена, печатаем полный путь, который искали
            print(f"❌ КАРТИНКА НЕ НАЙДЕНА: {filename}")
            print(f"   Искали в: {[str(p) for p in possible_paths]}")
            
            # Возвращаем заглушку, чтобы обучение не упало, но метрики будут 0
                        # Возвращаем заглушку (исправленная версия)
            dummy_img = Image.new("RGB", (256, 256))
            image_inputs = processor.image_processor(dummy_img, return_tensors="pt")
            label_inputs = processor.tokenizer("<s></s>", max_length=max_length, padding="max_length", truncation=True, return_tensors="pt")
            
            return {
                "pixel_values": image_inputs["pixel_values"].squeeze(0),
                "labels": label_inputs["input_ids"].squeeze(0)
            }

        try:
            image = Image.open(image_path).convert("RGB")
        except Exception as e:
            print(f"❌ ОШИБКА ОТКРЫТИЯ ФАЙЛА {image_path}: {e}")
            encoding = processor(
                Image.new("RGB", (256, 256)), 
                "<s></s>", 
                max_length=max_length, 
                padding="max_length", 
                truncation=True, 
                return_tensors="pt"
            )
            return {
                "pixel_values": encoding["pixel_values"].squeeze(0),
                "labels": encoding["input_ids"].squeeze(0)
            }
        
        # Извлечение gt_parse (с поддержкой обоих форматов)
        gt_parse = entry.get("gt_parse", {})
        
        # Если ground_truth - строка, распарсим
        if not gt_parse and "ground_truth" in entry:
            ground_truth = entry["ground_truth"]
            if isinstance(ground_truth, str):
                try:
                    nested = json.loads(ground_truth)
                    gt_parse = nested.get("gt_parse", nested)
                except:
                    gt_parse = {}
        
        # Если gt_parse - строка, распарсим
        if isinstance(gt_parse, str):
            try:
                gt_parse = json.loads(gt_parse)
            except:
                gt_parse = {}
        
        # Формирование target последовательности
        target_tokens = []
        for field in LABEL_LIST:
            if field in gt_parse and gt_parse[field]:
                target_tokens.append(f"<s_{field}>")
                target_tokens.append(str(gt_parse[field]).strip())
                target_tokens.append(f"</s_{field}>")
        
        # Токенизация
        # 1. Обрабатываем изображение отдельно
        image_inputs = processor.image_processor(
            image, 
            return_tensors="pt"
        )
        
        # 2. Обрабатываем текст отдельно
        text_target = " ".join(target_tokens) if target_tokens else "<s></s>"
        label_inputs = processor.tokenizer(
            text_target,
            max_length=max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )
        
        # 3. Собираем всё вместе
        encoding = {
            "pixel_values": image_inputs["pixel_values"].squeeze(0),
            "labels": label_inputs["input_ids"].squeeze(0)
        }
        
        return encoding
        
        return {
            "pixel_values": encoding["pixel_values"].squeeze(0),
            "labels": encoding["input_ids"].squeeze(0)
        }
    
    dataset = Dataset.from_list(entries)
    dataset = dataset.map(preprocess, remove_columns=dataset.column_names)
    
    print(f"✅ Датасет готов: {len(dataset)} примеров")
    return dataset

def compute_metrics(eval_pred):
    """Вычисляет метрики качества."""
    predictions, labels = eval_pred
    predictions = np.argmax(predictions, axis=-1)
    
    # Декодирование
    pred_texts = processor.batch_decode(predictions, skip_special_tokens=False)
    label_texts = processor.batch_decode(labels, skip_special_tokens=False)
    
    # Парсинг и сравнение
    correct_fields = 0
    total_fields = 0
    
    for pred, label in zip(pred_texts, label_texts):
        pred_fields = parse_donut_output(pred)
        label_fields = parse_donut_output(label)
        
        for field in LABEL_LIST:
            if field in label_fields:
                total_fields += 1
                if field in pred_fields and pred_fields[field] == label_fields[field]:
                    correct_fields += 1
    
    return {
        "field_accuracy": correct_fields / total_fields if total_fields > 0 else 0
    }

def train():
    """Основная функция обучения."""
    global processor
    train_config = config.get("donut", {}).get("train", {})
    
    # Инициализация процессора и модели
    print("🔄 Загрузка процессора и модели...")
        # Правильная инициализация полного процессора
    processor = DonutProcessor.from_pretrained(config["donut"]["model_name"])
    
    model = VisionEncoderDecoderModel.from_pretrained(config["donut"]["model_name"])
    
    # Настройка модели
    model.config.decoder_start_token_id = processor.tokenizer.cls_token_id
    model.config.pad_token_id = processor.tokenizer.pad_token_id
    model.config.max_length = config["donut"]["max_length"]
    
    # Загрузка датасетов
    print("📊 Загрузка датасетов...")
    train_dataset = load_dataset(
        "dataset/train/metadata.jsonl",  # ← ИСПРАВЛЕННЫЙ ПУТЬ
        processor,
        config["donut"]["max_length"]
    )
    
    # Валидационный датасет (опционально)
    val_dataset = None
    if Path("dataset/val/metadata.jsonl").exists():
        val_dataset = load_dataset(
            "dataset/val/metadata.jsonl",
            processor,
            config["donut"]["max_length"]
        )
    else:
        print("⚠️ Валидационный датасет не найден, используем train для валидации")
        val_dataset = train_dataset
    
    # Настройка обучения
    training_args = TrainingArguments(
        output_dir=train_config["output_dir"],
        per_device_train_batch_size=train_config["batch_size"],
        per_device_eval_batch_size=train_config["batch_size"],
        num_train_epochs=train_config["num_epochs"],
        learning_rate=train_config["learning_rate"],
        warmup_steps=train_config["warmup_steps"],
        gradient_accumulation_steps=train_config.get("gradient_accumulation", 1),
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="field_accuracy",
        logging_dir=f"{train_config['output_dir']}/logs",
        logging_steps=10,
        save_total_limit=3,
        fp16=torch.cuda.is_available(),
        push_to_hub=False,
    )
    
    # Trainer
    print("🔧 Инициализация Trainer...")
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
    )
    
    # Обучение
    print("🚀 Начало обучения...")
    try:
        trainer.train()
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА ПРИ ОБУЧЕНИИ: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return  # Прерываем выполнение, чтобы не пытаться сохранять битую модель

    # Сохранение
    print(f"💾 Сохранение модели в {train_config['output_dir']}...")
    trainer.save_model(train_config["output_dir"])
    processor.save_pretrained(train_config["output_dir"])
    
    print("✅ Обучение завершено!")

if __name__ == "__main__":
    train()