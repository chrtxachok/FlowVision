# scripts/split_dataset.py
import json
from pathlib import Path
from sklearn.model_selection import train_test_split

def split_dataset(data_path: str, output_dir: str):
    """Разделяет датасет на train/val/test (70/15/15)."""
    
    with open(data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Первое разделение: train vs temp (70/30)
    train_data, temp_data = train_test_split(
        data, 
        test_size=0.3, 
        random_state=42
    )
    
    # Второе разделение: val vs test (50/50 от temp)
    val_data, test_data = train_test_split(
        temp_data, 
        test_size=0.5, 
        random_state=42
    )
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Сохраните разделения
    with open(output_path / "train.json", 'w', encoding='utf-8') as f:
        json.dump(train_data, f, ensure_ascii=False, indent=2)
    
    with open(output_path / "val.json", 'w', encoding='utf-8') as f:
        json.dump(val_data, f, ensure_ascii=False, indent=2)
    
    with open(output_path / "test.json", 'w', encoding='utf-8') as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    
    print(f"Train: {len(train_data)}, Val: {len(val_data)}, Test: {len(test_data)}")

if __name__ == "__main__":
    split_dataset(
        data_path="data/processed/layoutlm/data.json",
        output_dir="data/processed/layoutlm/splits"
    )