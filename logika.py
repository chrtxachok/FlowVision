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
# ПОСТОБРАБОТКА ПОЛЕЙ
# ------------------------------------------------------------
def postprocess_field(field_id, text):
    if not text or len(text) < 2:
        return None
    text = text.replace('«', '"').replace('»', '"')
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'[{}|<>\[\]()]', '', text)
    text = re.sub(r'[^А-ЯЁа-яё0-9\s\-\.\,:\/№"]', '', text)

    if field_id == 'F001':
        match = re.search(r'(\d{3,4}[-]?\d{3,6})', text)
        return match.group(1) if match else None
    elif field_id == 'F002':
        match = re.search(r'(\d{2}\.\d{2}\.\d{2,4})', text)
        return match.group(1) if match else None
    elif field_id == 'F003':
        text = re.sub(r'ИНН\s*\d+', '', text)
        text = re.sub(r'КПП\s*\d+', '', text)
        text = re.sub(r'[;/]', ' ', text)
        text = ' '.join(text.split())
        text = text.strip('"\'')
        if re.search(r'[А-ЯЁ][а-яё]', text):
            return text[:60]
        return None
    elif field_id == 'F004':
        text = re.sub(r'ИНН\s*\d+', '', text)
        text = re.sub(r'КПП\s*\d+', '', text)
        text = ' '.join(text.split())
        text = text.strip('"\'')
        if re.search(r'[А-ЯЁ][а-яё]', text):
            return text[:60]
        return None
    elif field_id == 'F005':
        match = re.search(r'(\d[\d\s]*\d)\s*руб', text)
        if match:
            return match.group(1).replace(' ', '') + ' руб.'
        match = re.search(r'(\d{3,})', text)
        if match:
            return match.group(1) + ' руб.'
        return None
    elif field_id == 'F006':
        garbage = ['отачнсе', 'нанменованне', 'вд переадресовю', 'на бумажном носитепе',
                   'отгрузачнсе', 'для опасных Рузов', 'допог', 'клИ']
        for g in garbage:
            text = text.replace(g, '')
        text = re.sub(r'\([^)]*\)', '', text)
        text = re.sub(r'[^А-ЯЁа-яё0-9\s\-/]', '', text)
        text = ' '.join(text.split())
        if len(text) > 2:
            return text[:60]
        return None
    elif field_id == 'F007':
        if re.search(r'Стоимость перевозки|установленная плата|продолжение', text, re.IGNORECASE):
            return None
        text = re.sub(r'ИНН\s*\d+', '', text)
        text = ' '.join(text.split())
        text = text.strip('"\'')
        if re.search(r'[А-ЯЁ][а-яё]', text):
            return text[:50]
        return None
    elif field_id in ['F008', 'F009', 'F017']:
        match = re.search(r'ИНН\s*(\d{10,12})', text)
        if match:
            return f"ИНН {match.group(1)}"
        match = re.search(r'\b(\d{10,12})\b', text)
        if match:
            return f"ИНН {match.group(1)}"
        return None
    elif field_id in ['F010', 'F011']:
        match = re.search(r'КПП\s*(\d{9})', text)
        if match:
            return f"КПП {match.group(1)}"
        match = re.search(r'\b(\d{9})\b', text)
        if match:
            return f"КПП {match.group(1)}"
        return None
    elif field_id in ['F013', 'F014']:
        match = re.search(r'№?\s*(\d+)\s+от\s+(\d{2}\.\d{2}\.\d{2,4})', text)
        if match:
            return f"№{match.group(1)} от {match.group(2)}"
        return None
    elif field_id in ['F015', 'F016']:
        match = re.search(r'(\d{2}\.\d{2}\.\d{2,4})[,.]?\s*(\d{2}:\d{2})?', text)
        if match:
            date = match.group(1)
            time = match.group(2) if match.group(2) else ""
            return f"{date}, {time}".strip(', ')
        return None
    elif field_id == 'F018':
        match = re.search(r'([А-ЯЁ][а-яё]+)\s+([А-ЯЁ][а-яё]+)\s+([А-ЯЁ][а-яё]+)', text)
        if match:
            return f"{match.group(1)} {match.group(2)} {match.group(3)}"
        match = re.search(r'([А-ЯЁ][а-яё]+)\s+([А-ЯЁ][а-яё]+)', text)
        if match:
            return f"{match.group(1)} {match.group(2)}"
        return None
    elif field_id == 'F019':
        match = re.search(r'([А-Я]{1,2})\s*(\d{3})\s*([А-Я]{1,2})\s*(\d{2,3})?', text.upper())
        if match:
            return f"{match.group(1)}{match.group(2)}{match.group(3)}{match.group(4) if match.group(4) else ''}"
        return None
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
    result = {}
    group1_texts = []
    for fid in ['F003', 'F008', 'F010']:
        if output.get(fid):
            group1_texts.extend(output[fid])
    if group1_texts:
        full = " ".join(group1_texts)
        org_match = re.search(r'^([^ИНН]+?)(?=ИНН|$)', full)
        if org_match:
            org = org_match.group(1).strip()
            org = re.sub(r'КПП\s*\d+', '', org)
            org = ' '.join(org.split())
            if re.search(r'[А-ЯЁ][а-яё]', org) and len(org) > 2:
                result['F003'] = org[:60]
        inn_match = re.search(r'ИНН\s*(\d{10,12})', full)
        if inn_match:
            result['F008'] = f"ИНН {inn_match.group(1)}"
        kpp_match = re.search(r'КПП\s*(\d{9})', full)
        if kpp_match:
            result['F010'] = f"КПП {kpp_match.group(1)}"
    
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
# Распознавание документа (быстрая версия ROI)
# ------------------------------------------------------------
def process_document(image_path, avg_coords, reader, iou_threshold=0.15):
    img = imread_unicode(image_path)
    if img is None:
        raise ValueError(f"Не удалось загрузить {image_path}")
    h_img, w_img = img.shape[:2]

    output = {fid: [] for fid in avg_coords.keys()}
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

    padding_config = {
        'F001': 1.0,
        'F002': 1.0,
        'F003': 1.0,
        'F004': 1.0,
        'F010': 0.8,
        'F013': 0.8,
        'F014': 0.8,
        'F017': 0.6,
        'F005': 0.5,
        'default': 0.3
    }

    def get_text_from_roi(x_perc, y_perc, w_perc, h_perc, field_id):
        x = int(x_perc / 100.0 * w_img)
        y = int(y_perc / 100.0 * h_img)
        w = int(w_perc / 100.0 * w_img)
        h = int(h_perc / 100.0 * h_img)
        pad_ratio = padding_config.get(field_id, padding_config['default'])
        pad_x = int(w * pad_ratio)
        pad_y = int(h * pad_ratio)
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

    for fid, (x, y, w, h) in adjusted_coords.items():
        texts = get_text_from_roi(x, y, w, h, fid)
        if texts:
            output[fid] = texts

    grouped = process_grouped_fields(output)
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
# Основной класс для использования в программе
# ------------------------------------------------------------
class WaybillExtractor:
    """
    Извлекатель данных из транспортной накладной.
    Поддерживает:
    - два изображения (первая и вторая страницы)
    - одно изображение (автоматическое определение страницы по наличию полей)
    """
    def __init__(self, json_path=None, model_dir='.'):
        self.model_dir = model_dir
        self.model_pkl = os.path.join(model_dir, 'field_classifier.pkl')
        self.scaler_pkl = os.path.join(model_dir, 'scaler.pkl')
        self.coords_pkl = os.path.join(model_dir, 'field_coords.pkl')
        self.reader = None
        self.avg_coords = None
        self._init_model(json_path)

    def _init_model(self, json_path):
        if os.path.exists(self.model_pkl) and os.path.exists(self.coords_pkl):
            _, _, self.avg_coords = load_model(self.model_pkl, self.scaler_pkl, self.coords_pkl)
        else:
            if json_path is None:
                raise ValueError("Модель не найдена. Укажите JSON-файл разметки для обучения.")

            _, _, self.avg_coords = train_model_from_json(json_path,
                                                          self.model_pkl,
                                                          self.scaler_pkl,
                                                          self.coords_pkl)
        self.reader = easyocr.Reader(['ru', 'en'], gpu=False)

    def _process_single_page(self, image_path, is_page_2=False):
        """
        Обрабатывает одно изображение как указанную страницу.
        :param is_page_2: True – вторая страница, False – первая.
        """
        current_coords = self.avg_coords.copy()
        if is_page_2:

            current_coords.pop("F006", None)
        fields = process_document(image_path, current_coords, self.reader)
        # Удаляем поля, которые не должны присутствовать на данной странице
        if is_page_2:
            fields.pop("F007", None)   # лишнее на второй странице
        else:
            fields.pop("F021", None)   # лишнее на первой странице
        return fields

    def _detect_page(self, image_path):

        # Сначала пробуем как первую страницу (с F006)
        coords1 = self.avg_coords.copy()
        fields1 = process_document(image_path, coords1, self.reader)
        # Проверяем наличие уникальных полей первой страницы
        if fields1.get("F001") or fields1.get("F006") or fields1.get("F002"):
            # Убираем лишнее для первой страницы
            fields1.pop("F021", None)
            return 1, fields1


        coords2 = self.avg_coords.copy()
        coords2.pop("F006", None)
        fields2 = process_document(image_path, coords2, self.reader)
        if fields2.get("F015") or fields2.get("F005") or fields2.get("F020"):
            fields2.pop("F007", None)
            return 2, fields2

        # Если ничего не найдено, возвращаем результат первой попытки (скорее всего пустой)
        return 0, {}

    def extract(self, images):
        """
        Извлекает поля из одного или двух изображений.
        :param images: строка (путь к одному файлу) или список из 1 или 2 путей
        :return: словарь с извлечёнными полями
        """
        # Приводим к списку
        if isinstance(images, str):
            images = [images]
        if not isinstance(images, (list, tuple)):
            raise TypeError("images должно быть str, list или tuple")

        if len(images) == 1:
            # Автоопределение страницы
            page, fields = self._detect_page(images[0])

            return fields
        elif len(images) == 2:
            # Явно первая и вторая страницы
            fields1 = self._process_single_page(images[0], is_page_2=False)
            fields2 = self._process_single_page(images[1], is_page_2=True)
            # Объединяем
            combined = {}
            combined.update(fields1)
            combined.update(fields2)
            return combined
        else:
            raise ValueError("Можно передать не более 2 изображений (одно или два).")
# ------------------------------------------------------------
# Пример использования (можно удалить или оставить для теста)
# ------------------------------------------------------------
# if __name__ == "__main__":
#     # При первом запуске укажите путь к JSON-файлу разметки
#     extractor = WaybillExtractor(json_path="project-1-at-2026-04-18-05-40-eb2e8e7a.json")
#     result = extractor.extract([
#         "dataset/train/waybill_0001_page_1.jpg",
#         "dataset/train/waybill_0001_page_2.jpg"
#     ])
#     # Вывод в JSON
#     print(json.dumps(result, ensure_ascii=False, indent=2))
    
    
# if __name__ == "__main__":
#     # Путь к JSON‑файлу разметки (если модель ещё не обучена)
#     json_file = "project-1-at-2026-04-18-05-40-eb2e8e7a.json"
    
#     # Создаём экстрактор один раз (загрузка моделей EasyOCR и обученной модели)
#     extractor = WaybillExtractor(json_path=json_file)
    
#     print("Extractor готов. Введите пути к одному или двум изображениям (через пробел).")
#     print("Для выхода введите 'exit' или пустую строку.\n")
    
#     while True:
#         user_input = input(">>> ").strip()
#         if user_input.lower() in ('exit', 'quit', ''):
#             break
        
#         # Разбиваем введённую строку на части – это пути к файлам
#         image_paths = user_input.split()
#         if not image_paths:
#             continue
        
#         try:
#             # Вызываем основной метод extract() – замеряется чистое время обработки
#             result = extractor.extract(image_paths)
#             print("\nРезультат:")
#             print(json.dumps(result, ensure_ascii=False, indent=2))
#             print()
#         except Exception as e:
#             print(f"Ошибка при обработке: {e}\n")