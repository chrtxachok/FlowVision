import json
import os

def convert_to_donut_format(input_json_path, output_jsonl_path):
    with open(input_json_path, 'r', encoding='utf-8') as f:
        ls_data = json.load(f)

    with open(output_jsonl_path, 'w', encoding='utf-8') as f_out:
        for entry in ls_data:
            # 1. Извлекаем имя файла
            # Label Studio добавляет префикс (хеш) к имени, убираем его
            raw_filename = entry['file_upload']
            filename = raw_filename.split('-', 1)[-1] if '-' in raw_filename else raw_filename
            
            # 2. Собираем разметку полей в словарь
            gt_dict = {}
            results = entry['annotations'][0]['result']
            
            # В Label Studio разметка разбита на части: 
            # одна часть хранит имя поля (label), другая - текст (textarea)
            # Они связаны общим ID внутри таска
            temp_data = {}
            for res in results:
                res_id = res.get('id')
                if res_id not in temp_data:
                    temp_data[res_id] = {}
                
                if 'rectanglelabels' in res['value']:
                    temp_data[res_id]['key'] = res['value']['rectanglelabels'][0]
                elif 'text' in res['value']:
                    temp_data[res_id]['value'] = res['value']['text'][0]

            # Очищаем и формируем финальный словарь для этой накладной
            final_parse = {}
            for res_id, content in temp_data.items():
                key = content.get('key')
                val = content.get('value')
                if key and val:
                    final_parse[key] = val

            # 3. Формируем строку в формате Donut
            # ВНИМАНИЕ: Donut требует, чтобы весь JSON был упакован в строку внутри поля ground_truth
            ground_truth = {
                "gt_parse": final_parse
            }
            
            jsonl_line = {
                "file_name": filename,
                "ground_truth": json.dumps(ground_truth, ensure_ascii=False)
            }
            
            # Записываем как одну строку в файл
            f_out.write(json.dumps(jsonl_line, ensure_ascii=False) + '\n')

# Запуск
convert_to_donut_format('dataset/raw/train.json', 'dataset/train/metadata.jsonl')
print("Конвертация завершена!")