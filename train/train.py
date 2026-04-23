import os
import json
import torch
from pathlib import Path
from PIL import Image
from torch.utils.data import Dataset, DataLoader
from transformers import DonutProcessor, VisionEncoderDecoderModel, VisionEncoderDecoderConfig
import pytorch_lightning as pl
from pytorch_lightning.callbacks import ModelCheckpoint

# --- КОНФИГУРАЦИЯ ---
class Config:
    max_epochs = 50
    check_val_every_n_epoch = 5
    gradient_clip_val = 1.0
    lr = 2e-5
    train_batch_size = 1 # Donut очень тяжелый, начните с 1
    num_workers = 2
    max_length = 512
    image_size = [1280, 960] # Важно для мелкого текста ТТН
    model_name_or_path = "./models/donut-base" # Путь к скачанной модели
    dataset_path = "data/dataset/train" # Где лежит metadata.jsonl и картинки

# --- DATASET ---
class DonutDataset(Dataset):
    def __init__(self, dataset_path, processor, max_length, split="train"):
        super().__init__()
        self.dataset_path = Path(dataset_path)
        self.processor = processor
        self.max_length = max_length
        self.split = split
        
        self.metadata = []
        with open(self.dataset_path / "metadata.jsonl", 'r', encoding='utf-8') as f:
            for line in f:
                self.metadata.append(json.loads(line))

    def __len__(self):
        return len(self.metadata)

    def __getitem__(self, idx):
        item = self.metadata[idx]
        
        # Загрузка изображения
        image = Image.open(self.dataset_path / item["file_name"]).convert("RGB")
        
        # Подготовка пикселей
        pixel_values = self.processor(image, random_padding=True, return_tensors="pt").pixel_values
        pixel_values = pixel_values.squeeze()

        # Подготовка текста (labels)
        target_sequence = item["ground_truth"]
        input_ids = self.processor.tokenizer(
            target_sequence,
            add_special_tokens=False,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        ).input_ids.squeeze()

        labels = input_ids.clone()
        labels[labels == self.processor.tokenizer.pad_token_id] = -100 # Игнорируем паддинг в потере (loss)

        return pixel_values, labels, target_sequence

# --- LIGHTNING MODULE ---
class DonutModelPLModule(pl.LightningModule):
    def __init__(self, config, processor, model):
        super().__init__()
        self.config = config
        self.processor = processor
        self.model = model

    def training_step(self, batch, batch_idx):
        pixel_values, labels, _ = batch
        outputs = self.model(pixel_values, labels=labels)
        loss = outputs.loss
        self.log("train_loss", loss, prog_bar=True)
        return loss

    def configure_optimizers(self):
        return torch.optim.AdamW(self.parameters(), lr=self.config.lr)

# --- MAIN ---
def train():
    cfg = Config()
    
    # 1. Загрузка процессора и модели
    processor = DonutProcessor.from_pretrained(cfg.model_name_or_path)
    model = VisionEncoderDecoderModel.from_pretrained(cfg.model_name_or_path)

    # 2. Добавление спец-токенов полей (из вашей разметки)
    new_tokens = [
        "<s_waybill_number>", "<s_document_date>", "<s_sender_name>", 
        "<s_recipient_name>", "<s_product_name>", "<s_carrier_name>",
        "<s_sender_inn>", "<s_recipient_inn>", "<s_total_amount>"
    ]
    processor.tokenizer.add_tokens(new_tokens)
    model.decoder.resize_token_embeddings(len(processor.tokenizer))
    
    # Добавляем стартовый токен задачи
    processor.tokenizer.add_special_tokens({"additional_special_tokens": ["<s_waybill>"]})
    model.config.pad_token_id = processor.tokenizer.pad_token_id
    model.config.decoder_start_token_id = processor.tokenizer.convert_tokens_to_ids("<s_waybill>")

    # 3. Подготовка данных
    train_dataset = DonutDataset(cfg.dataset_path, processor, cfg.max_length)
    train_loader = DataLoader(train_dataset, batch_size=cfg.train_batch_size, shuffle=True, num_workers=cfg.num_workers)

    # 4. Обучение
    model_module = DonutModelPLModule(cfg, processor, model)
    
    checkpoint_callback = ModelCheckpoint(
        dirpath="./models/donut-trained",
        filename="donut-waybill-{epoch:02d}-{train_loss:.2f}",
        save_top_k=3,
        monitor="train_loss",
    )

    trainer = pl.Trainer(
        accelerator="gpu" if torch.cuda.is_available() else "cpu",
        devices=1,
        max_epochs=cfg.max_epochs,
        gradient_clip_val=cfg.gradient_clip_val,
        callbacks=[checkpoint_callback],
    )

    trainer.fit(model_module, train_loader)

    # 5. Сохранение финальной модели
    model.save_pretrained("./models/donut-trained-final")
    processor.save_pretrained("./models/donut-trained-final")

if __name__ == "__main__":
    train()