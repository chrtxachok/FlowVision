import json
import numpy as np
import pickle
import os
import cv2
import easyocr
import re
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

# ------------------------------------------------------------
# Чтение изображения с Unicode-путём
# ------------------------------------------------------------
def imread_unicode(path):
    with open(path, 'rb') as f:
        data = f.read()
    return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)

# ------------------------------------------------------------
# Обучение модели (без изменений, только по JSON)
# ------------------------------------------------------------
def train_model_from_json(json_path, 
                          model_save_path='field_classifier.pkl',
                          scaler_save_path='scaler.pkl',
                          field_coords_path='field_coords.pkl'):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    X, y = [], []
    field_coords = {}

    for task in data:
        annotations = task.get('annotations', [])
        if not annotations:
            continue
        annotation = annotations[0]
        results = annotation.get('result', [])

        orig_w = orig_h = None
        for res in results:
            if res.get('type') == 'rectanglelabels':
                orig_w = res.get('original_width')
                orig_h = res.get('original_height')
                break
        if orig_w is None or orig_h is None:
            continue

        rect_to_field = {}
        for res in results:
            rid = res.get('id')
            if res.get('from_name') == 'field_id' and rid:
                choices = res.get('value', {}).get('choices', [])
                if choices:
                    rect_to_field[rid] = choices[0]

        for res in results:
            if res.get('type') != 'rectanglelabels':
                continue
            rid = res.get('id')
            if rid not in rect_to_field:
                continue
            field_id = rect_to_field[rid]
            val = res.get('value', {})
            x = val.get('x')
            yc = val.get('y')
            w = val.get('width')
            h = val.get('height')
            if None in (x, yc, w, h):
                continue

            x_center = x + w/2
            y_center = yc + h/2
            area = w * h
            aspect = w / h if h > 0 else 1
            X.append([x_center, y_center, w, h, area, aspect])
            y.append(field_id)

            if field_id not in field_coords:
                field_coords[field_id] = []
            field_coords[field_id].append((float(x), float(yc), float(w), float(h)))

    if not X:
        raise ValueError("Нет данных для обучения")

    X = np.array(X)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_scaled, y)

    avg_coords = {}
    for fid, coords_list in field_coords.items():
        avg_x = np.mean([c[0] for c in coords_list])
        avg_y = np.mean([c[1] for c in coords_list])
        avg_w = np.mean([c[2] for c in coords_list])
        avg_h = np.mean([c[3] for c in coords_list])
        avg_coords[fid] = (float(avg_x), float(avg_y), float(avg_w), float(avg_h))

    with open(model_save_path, 'wb') as f:
        pickle.dump(clf, f)
    with open(scaler_save_path, 'wb') as f:
        pickle.dump(scaler, f)
    with open(field_coords_path, 'wb') as f:
        pickle.dump(avg_coords, f)

    print(f"Обучено на {len(X)} примерах. Поля: {list(avg_coords.keys())}")
    return clf, scaler, avg_coords

def load_model(model_path='field_classifier.pkl', 
               scaler_path='scaler.pkl', 
               coords_path='field_coords.pkl'):
    with open(model_path, 'rb') as f:
        clf = pickle.load(f)
    with open(scaler_path, 'rb') as f:
        scaler = pickle.load(f)
    with open(coords_path, 'rb') as f:
        avg_coords = pickle.load(f)
    avg_coords = {k: (float(v[0]), float(v[1]), float(v[2]), float(v[3])) for k, v in avg_coords.items()}
    return clf, scaler, avg_coords

# ------------------------------------------------------------
# ПОСТОБРАБОТКА ПОЛЕЙ (старая, но с добавлением чистки)
# ------------------------------------------------------------
def postprocess_field(field_id, text):
    if not text or len(text) < 2:
        return None
    # Замена кавычек-ёлочек
    text = text.replace('«', '"').replace('»', '"')
    # Убираем мусор
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'[{}|<>\[\]()]', '', text)
    text = re.sub(r'[^А-ЯЁа-яё0-9\s\-\.\,:\/№"]', '', text)

    # ---------- F001: номер накладной ----------
    if field_id == 'F001':
        match = re.search(r'(\d{3,4}[-]?\d{3,6})', text)
        return match.group(1) if match else None

    # ---------- F002: дата документа ----------
    elif field_id == 'F002':
        match = re.search(r'(\d{2}\.\d{2}\.\d{2,4})', text)
        return match.group(1) if match else None

    # ---------- F003: отправитель (убираем ИНН/КПП) ----------
    elif field_id == 'F003':
        text = re.sub(r'ИНН\s*\d+', '', text)
        text = re.sub(r'КПП\s*\d+', '', text)
        text = re.sub(r'[;/]', ' ', text)
        text = ' '.join(text.split())
        text = text.strip('"\'')
        if re.search(r'[А-ЯЁ][а-яё]', text):
            return text[:60]
        return None

    # ---------- F004: получатель ----------
    elif field_id == 'F004':
        text = re.sub(r'ИНН\s*\d+', '', text)
        text = re.sub(r'КПП\s*\d+', '', text)
        text = ' '.join(text.split())
        text = text.strip('"\'')
        if re.search(r'[А-ЯЁ][а-яё]', text):
            return text[:60]
        return None

    # ---------- F005: сумма ----------
    elif field_id == 'F005':
        match = re.search(r'(\d[\d\s]*\d)\s*руб', text)
        if match:
            return match.group(1).replace(' ', '') + ' руб.'
        match = re.search(r'(\d{3,})', text)
        if match:
            return match.group(1) + ' руб.'
        return None

    # ---------- F006: товар (усиленная фильтрация) ----------
    elif field_id == 'F006':
        # Удаляем конкретные мусорные фразы
        garbage = ['отачнсе', 'нанменованне', 'вд переадресовю', 'на бумажном носитепе',
                   'отгрузачнсе', 'для опасных Рузов', 'допог', 'клИ']
        for g in garbage:
            text = text.replace(g, '')
        # Убираем скобки, лишние символы
        text = re.sub(r'\([^)]*\)', '', text)
        text = re.sub(r'[^А-ЯЁа-яё0-9\s\-/]', '', text)
        text = ' '.join(text.split())
        if len(text) > 2:
            return text[:60]   # увеличил до 60 символов
        return None

    # ---------- F007: перевозчик (фильтрация) ----------
    elif field_id == 'F007':
        # Отбрасываем явно не подходящие строки
        if re.search(r'Стоимость перевозки|установленная плата|продолжение', text, re.IGNORECASE):
            return None
        text = re.sub(r'ИНН\s*\d+', '', text)
        text = ' '.join(text.split())
        text = text.strip('"\'')
        if re.search(r'[А-ЯЁ][а-яё]', text):
            return text[:50]
        return None

    # ---------- F008, F009, F017: ИНН ----------
    elif field_id in ['F008', 'F009', 'F017']:
        match = re.search(r'ИНН\s*(\d{10,12})', text)
        if match:
            return f"ИНН {match.group(1)}"
        match = re.search(r'\b(\d{10,12})\b', text)
        if match:
            return f"ИНН {match.group(1)}"
        return None

    # ---------- F010, F011: КПП ----------
    elif field_id in ['F010', 'F011']:
        match = re.search(r'КПП\s*(\d{9})', text)
        if match:
            return f"КПП {match.group(1)}"
        match = re.search(r'\b(\d{9})\b', text)
        if match:
            return f"КПП {match.group(1)}"
        return None

    # ---------- F013, F014: номер договора/счёта ----------
    elif field_id in ['F013', 'F014']:
        match = re.search(r'№?\s*(\d+)\s+от\s+(\d{2}\.\d{2}\.\d{2,4})', text)
        if match:
            return f"№{match.group(1)} от {match.group(2)}"
        return None

    # ---------- F015, F016: дата+время ----------
    elif field_id in ['F015', 'F016']:
        match = re.search(r'(\d{2}\.\d{2}\.\d{2,4})[,.]?\s*(\d{2}:\d{2})?', text)
        if match:
            date = match.group(1)
            time = match.group(2) if match.group(2) else ""
            return f"{date}, {time}".strip(', ')
        return None

    # ---------- F018: ФИО водителя ----------
    elif field_id == 'F018':
        match = re.search(r'([А-ЯЁ][а-яё]+)\s+([А-ЯЁ][а-яё]+)\s+([А-ЯЁ][а-яё]+)', text)
        if match:
            return f"{match.group(1)} {match.group(2)} {match.group(3)}"
        match = re.search(r'([А-ЯЁ][а-яё]+)\s+([А-ЯЁ][а-яё]+)', text)
        if match:
            return f"{match.group(1)} {match.group(2)}"
        return None

    # ---------- F019: номер ТС ----------
    elif field_id == 'F019':
        match = re.search(r'([А-Я]{1,2})\s*(\d{3})\s*([А-Я]{1,2})\s*(\d{2,3})?', text.upper())
        if match:
            return f"{match.group(1)}{match.group(2)}{match.group(3)}{match.group(4) if match.group(4) else ''}"
        return None

    # ---------- F020, F021: адреса ----------
    elif field_id in ['F020', 'F021']:
        stop_words = ['грузоотправитель', 'перевозчик', 'получатель', 'рузоотправитель', 'клх', 'ст', 'алл']
        for w in stop_words:
            text = re.sub(rf'\b{w}\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s+', ' ', text).strip()
        if len(text) > 5:
            return text[:80]
        return None

    else:
        return text[:50]

# ------------------------------------------------------------
# Групповая постобработка для слитых полей
# ------------------------------------------------------------
def process_grouped_fields(output):
    """
    Принимает словарь output {field_id: [list_of_texts]},
    возвращает словарь с исправленными значениями для групп.
    """
    result = {}
    
    # Группа 1: Отправитель (F003) + ИНН (F008) + КПП (F010)
    group1_texts = []
    for fid in ['F003', 'F008', 'F010']:
        if output.get(fid):
            group1_texts.extend(output[fid])
    if group1_texts:
        full = " ".join(group1_texts)
        # Ищем организацию (до слова ИНН или до конца)
        org_match = re.search(r'^([^ИНН]+?)(?=ИНН|$)', full)
        if org_match:
            org = org_match.group(1).strip()
            org = re.sub(r'КПП\s*\d+', '', org)
            org = ' '.join(org.split())
            if re.search(r'[А-ЯЁ][а-яё]', org) and len(org) > 2:
                result['F003'] = org[:60]
        # ИНН
        inn_match = re.search(r'ИНН\s*(\d{10,12})', full)
        if inn_match:
            result['F008'] = f"ИНН {inn_match.group(1)}"
        # КПП
        kpp_match = re.search(r'КПП\s*(\d{9})', full)
        if kpp_match:
            result['F010'] = f"КПП {kpp_match.group(1)}"
    
    # Группа 2: Получатель (F004) + ИНН (F009) + КПП (F011)
    group2_texts = []
    for fid in ['F004', 'F009', 'F011']:
        if output.get(fid):
            group2_texts.extend(output[fid])
    if group2_texts:
        full = " ".join(group2_texts)
        org_match = re.search(r'^([^ИНН]+?)(?=ИНН|$)', full)
        if org_match:
            org = org_match.group(1).strip()
            org = re.sub(r'КПП\s*\d+', '', org)
            org = ' '.join(org.split())
            if re.search(r'[А-ЯЁ][а-яё]', org) and len(org) > 2:
                result['F004'] = org[:60]
        inn_match = re.search(r'ИНН\s*(\d{10,12})', full)
        if inn_match:
            result['F009'] = f"ИНН {inn_match.group(1)}"
        kpp_match = re.search(r'КПП\s*(\d{9})', full)
        if kpp_match:
            result['F011'] = f"КПП {kpp_match.group(1)}"
    
    # Группа 3: Перевозчик (F007) + ИНН (F017)
    group3_texts = []
    for fid in ['F007', 'F017']:
        if output.get(fid):
            group3_texts.extend(output[fid])
    if group3_texts:
        full = " ".join(group3_texts)
        org_match = re.search(r'^([^ИНН]+?)(?=ИНН|$)', full)
        if org_match:
            org = org_match.group(1).strip()
            org = ' '.join(org.split())
            if re.search(r'[А-ЯЁ][а-яё]', org) and len(org) > 2:
                result['F007'] = org[:50]
        inn_match = re.search(r'ИНН\s*(\d{10,12})', full)
        if inn_match:
            result['F017'] = f"ИНН {inn_match.group(1)}"
    
    return result

# ------------------------------------------------------------
# Распознавание документа (старая логика IOU, без расширения)
# ------------------------------------------------------------
def process_document(image_path, avg_coords, reader, iou_threshold=0.15):
    """
    Быстрая версия: OCR только по зонам полей (ROI) с большим запасом.
    """
    img = imread_unicode(image_path)
    if img is None:
        raise ValueError(f"Не удалось загрузить {image_path}")
    h_img, w_img = img.shape[:2]

    # Словарь для сбора текста по полям
    output = {fid: [] for fid in avg_coords.keys()}

    # Для F006 увеличиваем зону агрессивно (как в старом коде)
    adjusted_coords = dict(avg_coords)
    if 'F006' in adjusted_coords:
        x, y, w, h = adjusted_coords['F006']
        shift_up = 4
        width_scale = 2.0
        height_scale = 4.0
        new_x = x
        new_y = max(0, y - shift_up)
        new_w = min(100 - new_x, w * width_scale)
        new_h = h * height_scale
        adjusted_coords['F006'] = (new_x, new_y, new_w, new_h)

    # Определяем индивидуальный запас для каждого поля (в процентах от размера ROI)
    padding_config = {
        'F001': 1.0,   # 100% запаса – ищем по всей верхней части
        'F002': 1.0,# 100% запаса
        'F010': 0.8,
        'F013': 0.8,
        'F014': 0.8,
        'F017': 0.6,
        'F005': 0.5,
        'default': 0.3   # 30% запаса для остальных
    }

    def get_text_from_roi(x_perc, y_perc, w_perc, h_perc, field_id):
        # Переводим проценты в пиксели
        x = int(x_perc / 100.0 * w_img)
        y = int(y_perc / 100.0 * h_img)
        w = int(w_perc / 100.0 * w_img)
        h = int(h_perc / 100.0 * h_img)
        
        # Определяем запас
        pad_ratio = padding_config.get(field_id, padding_config['default'])
        pad_x = int(w * pad_ratio)
        pad_y = int(h * pad_ratio)
        # Но не более 100 пикселей и не менее 10
        pad_x = min(100, max(10, pad_x))
        pad_y = min(100, max(10, pad_y))
        
        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(w_img, x + w + pad_x)
        y2 = min(h_img, y + h + pad_y)
        
        roi = img[y1:y2, x1:x2]
        if roi.size == 0:
            return []
        try:
            results = reader.readtext(roi)
            texts = [item[1] for item in results if isinstance(item, (list, tuple)) and len(item) >= 2]
            return texts
        except:
            return []

    # Обрабатываем каждое поле
    for fid, (x, y, w, h) in adjusted_coords.items():
        texts = get_text_from_roi(x, y, w, h, fid)
        if texts:
            output[fid] = texts

    # Групповая обработка (объединяет отправитель+ИНН+КПП и т.д.)
    grouped = process_grouped_fields(output)

    # Постобработка каждого поля
    result = {}
    for fid, texts in output.items():
        if fid in grouped:
            continue
        if texts:
            raw = " ".join(texts)
            cleaned = postprocess_field(fid, raw)
            if cleaned:
                result[fid] = cleaned
    result.update(grouped)

    return result

# ------------------------------------------------------------
# Основной блок
# ------------------------------------------------------------
if __name__ == "__main__":
    json_file = "project-1-at-2026-04-18-05-40-eb2e8e7a.json"
    model_pkl = "field_classifier.pkl"
    scaler_pkl = "scaler.pkl"
    coords_pkl = "field_coords.pkl"

    if os.path.exists(model_pkl) and os.path.exists(coords_pkl):
        print("Загрузка существующей модели...")
        _, _, avg_coords = load_model(model_pkl, scaler_pkl, coords_pkl)
    else:
        print("Обучение модели по JSON...")
        _, _, avg_coords = train_model_from_json(json_file, model_pkl, scaler_pkl, coords_pkl)

    reader = easyocr.Reader(['ru', 'en'], gpu=True)

    image_paths = [
        r"dataset/train/waybill_0002_page_1.jpg",
        r"dataset/train/waybill_0002_page_2.jpg"
    ]

    for path in image_paths:
        if not os.path.exists(path):
            print(f"Файл не найден: {path}")
            continue
        print(f"\n=== Обработка {path} ===")

        # Создаём копию координат для текущего файла
        current_coords = avg_coords.copy()
        if "_page_2" in path:
            current_coords.pop("F006", None)   # удаляем F006 для второй страницы

        try:
            fields = process_document(path, current_coords, reader, iou_threshold=0.15)

            # Удаляем ненужные поля в зависимости от страницы
            if "_page_1" in path:
                fields.pop("F021", None)   # убираем F021 с первой страницы
            elif "_page_2" in path:
                fields.pop("F007", None)   # убираем F007 со второй страницы

            if not fields:
                print("Не удалось распознать ни одного поля.")
            else:
                for fid in sorted(fields.keys()):
                    print(f"{fid}: {fields[fid]}")
        except Exception as e:
            print(f"Ошибка: {e}")