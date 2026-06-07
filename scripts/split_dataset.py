# scripts/split_donut_dataset.py
import json
import random
from pathlib import Path
from sklearn.model_selection import train_test_split


def split_dataset(input_dir: str, output_base: str, train_ratio: float = 0.8):
    """Разделяет датасет Donut на train/val/test."""
    
    # Загрузка metadata
    with open(Path(input_dir) / "train" / "metadata.jsonl", 'r', encoding='utf-8') as f:
        entries = [json.loads(line) for line in f if line.strip()]
    
    random.seed(42)
    
    # Разделение
    train_entries, temp_entries = train_test_split(
        entries, train_size=train_ratio, random_state=42
    )
    val_entries, test_entries = train_test_split(
        temp_entries, train_size=0.5, random_state=42
    )
    
    # Копирование файлов и запись metadata
    for split_name, split_entries in [("train", train_entries), ("val", val_entries), ("test", test_entries)]:
        split_path = Path(output_base) / split_name
        split_path.mkdir(parents=True, exist_ok=True)
        
        images_src = Path(input_dir) / "train" / "images"
        images_dst = split_path / "images"
        images_dst.mkdir(exist_ok=True)
        
        metadata_lines = []
        
        for entry in split_entries:
            # Копирование изображения
            src_image = images_src / entry["file_name"].replace("images/", "")
            dst_image = images_dst / Path(entry["file_name"]).name
            
            if src_image.exists():
                import shutil
                shutil.copy2(src_image, dst_image)
            
            # Обновление пути
            entry["file_name"] = f"images/{Path(entry['file_name']).name}"
            metadata_lines.append(json.dumps(entry, ensure_ascii=False))
        
        # Запись metadata.jsonl
        with open(split_path / "metadata.jsonl", 'w', encoding='utf-8') as f:
            f.write('\n'.join(metadata_lines))
        
        print(f"✅ {split_name}: {len(split_entries)} документов")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--ratio", type=float, default=0.8)
    args = parser.parse_args()
    
    split_dataset(args.input, args.output, args.ratio)