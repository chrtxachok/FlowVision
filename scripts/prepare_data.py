# scripts/prepare_data.py
import json
import os
import shutil
from pathlib import Path

def convert_to_donut_format(input_json_path, output_jsonl_path, images_src_dir, images_dst_dir):
    """
    Конвертирует экспорт Label Studio в формат Donut для train.py
    
    Args:
        input_json_path: Путь к экспорту Label Studio (JSON)
        output_jsonl_path: Путь для выходного metadata.jsonl
        images_src_dir: Директория с исходными изображениями
        images_dst_dir: Директория для копирования изображений
    """
    
    # Загрузка данных из Label Studio
    with open(input_json_path, 'r', encoding='utf-8') as f:
        ls_data = json.load(f)
    
    # Создание директории для изображений
    Path(images_dst_dir).mkdir(parents=True, exist_ok=True)
    
    # Статистика
    stats = {"total": 0, "converted": 0, "errors": 0}
    
    with open(output_jsonl_path, 'w', encoding='utf-8') as f_out:
        for entry in ls_data:
            stats["total"] += 1
            
            try:
                # 1. Извлекаем имя файла
                raw_filename = entry.get('file_upload', '')
                if not raw_filename:
                    print(f"⚠️ Пропущено: нет file_upload")
                    stats["errors"] += 1
                    continue
                
                # Убираем хеш-префикс Label Studio
                filename = raw_filename.split('-', 1)[-1] if '-' in raw_filename else raw_filename
                
                # 2. Копируем изображение в целевую директорию
                src_path = Path(images_src_dir) / filename
                if not src_path.exists():
                    print(f"⚠️ Пропущено: изображение не найдено {src_path}")
                    stats["errors"] += 1
                    continue
                
                dst_path = Path(images_dst_dir) / filename
                shutil.copy2(src_path, dst_path)
                
                # 3. Собираем разметку полей в словарь
                gt_dict = {}
                results = entry.get('annotations', [{}])[0].get('result', [])
                
                if not results:
                    print(f"⚠️ Пропущено: нет аннотаций для {filename}")
                    stats["errors"] += 1
                    continue
                
                # В Label Studio разметка разбита на части:
                # одна часть хранит имя поля (rectanglelabels), другая - текст (textarea)
                # Они связаны общим ID внутри таска
                temp_data = {}
                for res in results:
                    res_id = res.get('id')
                    if res_id not in temp_data:
                        temp_data[res_id] = {}
                    
                    if 'rectanglelabels' in res.get('value', {}):
                        temp_data[res_id]['key'] = res['value']['rectanglelabels'][0]
                    elif 'text' in res.get('value', {}):
                        text_value = res['value'].get('text', [])
                        if text_value:
                            temp_data[res_id]['value'] = text_value[0]
                
                # Очищаем и формируем финальный словарь для этой накладной
                final_parse = {}
                for res_id, content in temp_data.items():
                    key = content.get('key')
                    val = content.get('value')
                    if key and val:
                        # Очистка текста от лишних пробелов
                        final_parse[key] = val.strip()
                
                if not final_parse:
                    print(f"⚠️ Пропущено: нет извлечённых полей для {filename}")
                    stats["errors"] += 1
                    continue
                
                # 4. Формируем строку в формате Donut
                # ИСПРАВЛЕНО: gt_parse напрямую, не в ground_truth как строка!
                jsonl_line = {
                    "file_name": f"{filename}",  # Путь относительно images_dst_dir
                    "gt_parse": final_parse  # ← ПРЯМОЙ СЛОВАРЬ, не строка!
                }
                
                # Записываем как одну строку в файл
                f_out.write(json.dumps(jsonl_line, ensure_ascii=False) + '\n')
                stats["converted"] += 1
                
            except Exception as e:
                print(f"❌ Ошибка обработки записи: {e}")
                stats["errors"] += 1
                continue
    
    # Вывод статистики
    print(f"\n{'='*50}")
    print(f"✅ Конвертация завершена!")
    print(f"{'='*50}")
    print(f"📊 Статистика:")
    print(f"   Всего записей: {stats['total']}")
    print(f"   Конвертировано: {stats['converted']}")
    print(f"   Ошибок: {stats['errors']}")
    print(f"📁 Выходной файл: {output_jsonl_path}")
    print(f"📁 Изображения: {images_dst_dir}")
    print(f"{'='*50}")
    
    return stats

# Запуск
if __name__ == "__main__":
    convert_to_donut_format(
        input_json_path='dataset/raw/train.json',
        output_jsonl_path='dataset/train/metadata.jsonl',
        images_src_dir='dataset/annotated',
        images_dst_dir='dataset/train/images'
    )