# scripts/convert_label_studio_to_layoutlm.py
import json
from pathlib import Path
from typing import List, Dict
import shutil

def convert_ls_to_layoutlm(ls_path: str, output_dir: str, images_dir: str):
    """Конвертирует экспорт Label Studio в формат для LayoutLM v3."""
    
    # Загрузите аннотации из Label Studio
    with open(ls_path, 'r', encoding='utf-8') as f:
        ls_data = json.load(f)
    
    # Создайте выходную директорию
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Маппинг лейблов из Label Studio в ID для LayoutLM
    label_map = {
        "waybill_number": 0,
        "document_date": 1,
        "sender_name": 2,
        "recipient_name": 3,
        "total_amount": 4,
        "sender_inn": 5,
        "recipient_inn": 6,
        "O": 7  # Outside (не поле)
    }
    
    # Обработайте каждый документ
    converted_data = []
    
    for item in ls_data:
        doc_id = item.get('id', f"doc_{item['id']}")
        image_path = item['data']['image']
        
        # Скопируйте изображение в директорию для обучения
        src_image = Path(images_dir) / image_path.split('/')[-1]
        dst_image = output_path / "images" / f"{doc_id}.png"
        dst_image.parent.mkdir(parents=True, exist_ok=True)
        
        if src_image.exists():
            shutil.copy(src_image, dst_image)
        
        # Извлеките аннотации
        annotations = item.get('annotations', [])
        if not annotations:
            continue
        
        words = []
        boxes = []
        labels = []
        
        for ann in annotations[0].get('result', []):
            value = ann.get('value', {})
            
            # Извлеките текст и bbox
            text = value.get('text', '')
            bbox = value.get('bbox', {})
            label = value.get('labels', ['O'])[0]
            
            if text and bbox:
                words.append(text)
                # Конвертируйте bbox из % в координаты 0-1000
                boxes.append([
                    int(bbox['x'] * 10),
                    int(bbox['y'] * 10),
                    int((bbox['x'] + bbox['width']) * 10),
                    int((bbox['y'] + bbox['height']) * 10)
                ])
                labels.append(label_map.get(label, 7))
        
        # Добавьте в конвертированные данные
        converted_data.append({
            "id": doc_id,
            "image_path": str(dst_image),
            "words": words,
            "boxes": boxes,
            "labels": labels
        })
    
    # Сохраните конвертированные данные
    with open(output_path / "data.json", 'w', encoding='utf-8') as f:
        json.dump(converted_data, f, ensure_ascii=False, indent=2)
    
    print(f"Конвертировано {len(converted_data)} документов в {output_path}")
    return converted_data

if __name__ == "__main__":
    convert_ls_to_layoutlm(
        ls_path="data/annotated/annotations.json",
        output_dir="data/processed/layoutlm",
        images_dir="data/raw"
    )