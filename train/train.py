#!/usr/bin/env python3
"""
Fine-tuning Donut для извлечения полей накладных (ТТН).

Режим для Tesla T4 (14 GB) и Colab Free:
  python train/train.py --lowmem
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytorch_lightning as pl
import torch
from PIL import Image
from pytorch_lightning.callbacks import EarlyStopping, ModelCheckpoint
from torch.utils.data import DataLoader, Dataset
from transformers import DonutProcessor, VisionEncoderDecoderModel

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.ocr.donut_format import (  # noqa: E402
    TASK_TOKEN,
    apply_processor_image_size,
    build_special_tokens,
    configure_model_special_tokens,
    document_id_from_filename,
    gt_parse_to_sequence,
    mask_leading_task_token_in_labels,
    parse_ground_truth_item,
    resize_image_keep_aspect,
)


class TrainConfig:
    max_epochs = 25
    gradient_clip_val = 1.0
    lr = 2e-5
    train_batch_size = 1
    accumulate_grad_batches = 4
    num_workers = 0
    max_length = 768
    val_ratio = 0.2
    early_stop_patience = 5
    model_name_or_path = str(ROOT / "models" / "donut-base")
    dataset_path = str(ROOT / "dataset" / "train")
    output_dir = str(ROOT / "models" / "donut-trained")
    final_dir = str(ROOT / "models" / "donut-trained-final")
    seed = 42

    # Память GPU (переопределяется в --lowmem)
    image_height = 0  # 0 = размер по умолчанию у processor
    image_width = 0
    use_fp16 = False
    gradient_checkpointing = False
    freeze_encoder = False
    random_padding = True


class TrainConfigLowMem(TrainConfig):
    """Профиль для Tesla T4 16 GB / Colab Free (~14.5 GiB usable)."""

    max_length = 512
    accumulate_grad_batches = 8
    image_height = 960
    image_width = 1280
    use_fp16 = True
    gradient_checkpointing = True
    freeze_encoder = False
    random_padding = False


class TrainConfigMinimal(TrainConfigLowMem):
    """Тестовый урезанный профиль (T4): только декодер, короткая последовательность."""

    max_epochs = 15
    max_length = 512
    accumulate_grad_batches = 16
    freeze_encoder = False
    output_dir = str(ROOT / "models" / "donut-trained-minimal")
    final_dir = str(ROOT / "models" / "donut-trained-minimal")


class DonutDataset(Dataset):
    def __init__(
        self,
        records: list[dict],
        dataset_path: Path,
        processor: DonutProcessor,
        max_length: int,
        image_height: int = 0,
        image_width: int = 0,
        random_padding: bool = True,
    ):
        self.records = records
        self.dataset_path = dataset_path
        self.processor = processor
        self.max_length = max_length
        self.image_height = image_height
        self.image_width = image_width
        self.random_padding = random_padding

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int):
        item = self.records[idx]
        image_path = self.dataset_path / item["file_name"]
        image = Image.open(image_path).convert("RGB")

        if self.image_height > 0 and self.image_width > 0:
            image = resize_image_keep_aspect(image, self.image_width, self.image_height)

        pixel_values = self.processor(
            image,
            random_padding=self.random_padding,
            return_tensors="pt",
        ).pixel_values.squeeze(0)

        target_sequence = item.get("target_sequence")
        if not target_sequence:
            gt = parse_ground_truth_item(item["ground_truth"])
            target_sequence = gt_parse_to_sequence(gt)

        input_ids = self.processor.tokenizer(
            target_sequence,
            add_special_tokens=False,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        ).input_ids.squeeze(0)

        labels = input_ids.clone()
        labels[labels == self.processor.tokenizer.pad_token_id] = -100
        mask_leading_task_token_in_labels(labels, input_ids, self.processor.tokenizer)

        return pixel_values, labels


def collate_fn(batch):
    pixel_values = torch.stack([b[0] for b in batch])
    labels = torch.stack([b[1] for b in batch])
    return pixel_values, labels


class DonutModelPLModule(pl.LightningModule):
    def __init__(self, config: TrainConfig, processor: DonutProcessor, model: VisionEncoderDecoderModel):
        super().__init__()
        self.config = config
        self.processor = processor
        self.model = model

    def _step(self, batch, stage: str):
        pixel_values, labels = batch
        outputs = self.model(pixel_values=pixel_values, labels=labels)
        loss = outputs.loss
        self.log(f"{stage}_loss", loss, prog_bar=True, on_step=(stage == "train"), on_epoch=True)
        return loss

    def on_train_epoch_start(self) -> None:
        if self.config.freeze_encoder:
            self.model.encoder.eval()
            self.model.decoder.train()
        else:
            self.model.train()

    def on_validation_epoch_start(self) -> None:
        self.model.eval()

    def training_step(self, batch, batch_idx):
        return self._step(batch, "train")

    def validation_step(self, batch, batch_idx):
        return self._step(batch, "val")

    def configure_optimizers(self):
        params = [p for p in self.model.parameters() if p.requires_grad]
        return torch.optim.AdamW(params, lr=self.config.lr)


def load_records(dataset_path: Path) -> list[dict]:
    meta_path = dataset_path / "metadata.jsonl"
    if not meta_path.exists():
        raise FileNotFoundError(f"Нет {meta_path}. Запустите: python scripts/prepare_data.py")

    records = []
    for line in meta_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))

    missing = [r["file_name"] for r in records if not (dataset_path / r["file_name"]).exists()]
    if missing:
        raise FileNotFoundError(
            f"Нет {len(missing)} изображений в {dataset_path}. "
            f"Пример: {missing[0]}. Запустите: python scripts/prepare_data.py"
        )
    return records


def split_by_document(records: list[dict], val_ratio: float, seed: int):
    doc_to_records: dict[str, list[dict]] = {}
    for r in records:
        doc_id = document_id_from_filename(r["file_name"])
        doc_to_records.setdefault(doc_id, []).append(r)

    doc_ids = sorted(doc_to_records.keys())
    generator = torch.Generator().manual_seed(seed)
    perm = torch.randperm(len(doc_ids), generator=generator).tolist()
    shuffled = [doc_ids[i] for i in perm]

    n_val = max(1, int(len(shuffled) * val_ratio))
    val_docs = set(shuffled[:n_val])

    train_recs, val_recs = [], []
    for doc_id, recs in doc_to_records.items():
        (val_recs if doc_id in val_docs else train_recs).extend(recs)
    return train_recs, val_recs


def setup_model_and_processor(cfg: TrainConfig):
    model_path = Path(cfg.model_name_or_path)
    if not model_path.exists():
        raise FileNotFoundError(
            f"Нет базовой модели: {model_path}\n"
            "Скачайте: python scripts/download_model.py"
        )

    processor = DonutProcessor.from_pretrained(cfg.model_name_or_path)
    model = VisionEncoderDecoderModel.from_pretrained(cfg.model_name_or_path)

    if cfg.image_height > 0 and cfg.image_width > 0:
        apply_processor_image_size(processor, cfg.image_height, cfg.image_width)

    special_tokens = build_special_tokens()
    processor.tokenizer.add_special_tokens({"additional_special_tokens": special_tokens})
    #model.resize_token_embeddings(len(processor.tokenizer))
    new_vocab_size = len(processor.tokenizer)
    model.decoder.resize_token_embeddings(new_vocab_size)
    model.config.decoder.vocab_size = new_vocab_size


    configure_model_special_tokens(model, processor)

    if cfg.gradient_checkpointing:
        model.gradient_checkpointing_enable()
        print("Gradient checkpointing: ON")

    if cfg.freeze_encoder:
        for param in model.encoder.parameters():
            param.requires_grad = False
        print("Encoder: FROZEN (только декодер обучается)")

    return processor, model


def print_gpu_memory(label: str = "") -> None:
    if not torch.cuda.is_available():
        return
    free, total = torch.cuda.mem_get_info(0)
    print(f"GPU {label}: free {free / 1024**3:.2f} GiB / total {total / 1024**3:.2f} GiB")


def train(
    fast: bool = False,
    lowmem: bool = False,
    minimal: bool = False,
    freeze_encoder: bool = False,
    max_epochs: int | None = None,
    early_stop_patience: int | None = None,
) -> None:
    if lowmem or minimal:
        os.environ.setdefault("PYTORCH_ALLOC_CONF", "expandable_segments:True")

    if minimal:
        cfg: TrainConfig = TrainConfigMinimal()
    elif lowmem:
        cfg = TrainConfigLowMem()
    else:
        cfg = TrainConfig()
    if freeze_encoder and not minimal:
        cfg.freeze_encoder = True
    if max_epochs is not None:
        cfg.max_epochs = max_epochs
    if early_stop_patience is not None:
        cfg.early_stop_patience = early_stop_patience

    pl.seed_everything(cfg.seed)

    if minimal:
        print(
            "Режим --minimal (тест): "
            f"image {cfg.image_width}x{cfg.image_height}, "
            f"max_length={cfg.max_length}, freeze_encoder=True, "
            "часть полей в разметке будет обрезана"
        )
    elif lowmem:
        print(
            "Режим --lowmem: "
            f"image {cfg.image_width}x{cfg.image_height}, "
            f"max_epochs={cfg.max_epochs}, "
            f"fp16={cfg.use_fp16}, "
            f"max_length={cfg.max_length}, "
            f"grad_ckpt={cfg.gradient_checkpointing}, "
            f"freeze_encoder={cfg.freeze_encoder}"
        )
    print_gpu_memory("before load")

    dataset_path = Path(cfg.dataset_path)
    records = load_records(dataset_path)
    train_recs, val_recs = split_by_document(records, cfg.val_ratio, cfg.seed)
    print(f"Датасет: train={len(train_recs)}, val={len(val_recs)}")

    processor, model = setup_model_and_processor(cfg)
    print_gpu_memory("after model load")

    ds_kwargs = dict(
        image_height=cfg.image_height,
        image_width=cfg.image_width,
        random_padding=cfg.random_padding,
    )
    train_ds = DonutDataset(train_recs, dataset_path, processor, cfg.max_length, **ds_kwargs)
    val_ds = DonutDataset(val_recs, dataset_path, processor, cfg.max_length, **ds_kwargs)

    # Проверка размера одного батча
    pv_sample, _ = train_ds[0]
    print(f"pixel_values shape: {tuple(pv_sample.shape)}")

    train_loader = DataLoader(
        train_ds,
        batch_size=cfg.train_batch_size,
        shuffle=True,
        num_workers=cfg.num_workers,
        collate_fn=collate_fn,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=cfg.train_batch_size,
        shuffle=False,
        num_workers=cfg.num_workers,
        collate_fn=collate_fn,
    )

    module = DonutModelPLModule(cfg, processor, model)

    checkpoint_cb = ModelCheckpoint(
        dirpath=cfg.output_dir,
        filename="donut-waybill-{epoch:02d}-{val_loss:.3f}",
        save_top_k=2,
        monitor="val_loss",
        mode="min",
    )
    early_stop = EarlyStopping(monitor="val_loss", patience=cfg.early_stop_patience, mode="min")

    use_gpu = torch.cuda.is_available()
    trainer_kwargs = dict(
        accelerator="gpu" if use_gpu else "cpu",
        devices=1,
        max_epochs=1 if fast else cfg.max_epochs,
        gradient_clip_val=cfg.gradient_clip_val,
        accumulate_grad_batches=cfg.accumulate_grad_batches,
        callbacks=[checkpoint_cb, early_stop],
        enable_progress_bar=True,
        log_every_n_steps=1,
    )
    if cfg.use_fp16 and use_gpu:
        trainer_kwargs["precision"] = "16-mixed"
    if fast:
        trainer_kwargs["limit_train_batches"] = 2
        trainer_kwargs["limit_val_batches"] = 1

    trainer = pl.Trainer(**trainer_kwargs)
    trainer.fit(module, train_loader, val_loader)

    best_ckpt = checkpoint_cb.best_model_path
    if best_ckpt:
        try:
            ckpt = torch.load(best_ckpt, map_location="cpu", weights_only=False)
        except TypeError:
            ckpt = torch.load(best_ckpt, map_location="cpu")
        state_dict = ckpt.get("state_dict", ckpt)
        cleaned = {
            k[len("model.") :] if k.startswith("model.") else k: v
            for k, v in state_dict.items()
        }
        model.load_state_dict(cleaned, strict=False)
        print(f"Сохраняем лучший checkpoint (val_loss): {best_ckpt}")
    else:
        print("Лучший checkpoint не найден, сохраняем веса последней эпохи")

    final_path = Path(cfg.final_dir)
    final_path.mkdir(parents=True, exist_ok=True)
    configure_model_special_tokens(model, processor)
    model.save_pretrained(final_path)
    processor.save_pretrained(final_path)
    print(f"Модель сохранена: {final_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fine-tune Donut for waybills")
    parser.add_argument("--fast", action="store_true", help="2 train + 1 val batch, 1 epoch")
    parser.add_argument(
        "--lowmem",
        action="store_true",
        help="Профиль для T4 16GB: resize 1280x960, fp16, grad checkpointing, max_length=512",
    )
    parser.add_argument(
        "--freeze-encoder",
        action="store_true",
        help="Заморозить энкодер (ещё меньше памяти, хуже качество). Используйте только если OOM остаётся",
    )
    parser.add_argument(
        "--minimal",
        action="store_true",
        help="Тестовый урезанный режим для T4: lowmem + freeze encoder + max_length=128",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=None,
        help="Число эпох (по умолчанию 25; для lowmem/minimal — из профиля)",
    )
    parser.add_argument(
        "--patience",
        type=int,
        default=None,
        help="Early stopping по val_loss (по умолчанию 5)",
    )
    args = parser.parse_args()
    train(
        fast=args.fast,
        lowmem=args.lowmem,
        minimal=args.minimal,
        freeze_encoder=args.freeze_encoder,
        max_epochs=args.epochs,
        early_stop_patience=args.patience,
    )
