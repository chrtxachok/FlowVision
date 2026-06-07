def calculate_metrics(preds, gts):
    """
    preds: список словарей, которые выдала модель
    gts: список словарей из разметки
    """
    # Мы считаем поле "правильным", если ключ есть и значение совпадает на 100%
    tp = 0 # Нашел поле и оно верное
    fp = 0 # Нашел лишнее поле или ошибся в значении
    fn = 0 # Не нашел поле, которое было в оригинале
    
    for p, g in zip(preds, gts):
        for key in g.keys():
            if key in p and p[key] == g[key]:
                tp += 1
            elif key in p and p[key] != g[key]:
                fp += 1
            else:
                fn += 1
                
    precision = tp / (tp + fp + 1e-9)
    recall = tp / (tp + fn + 1e-9)
    f1 = 2 * (precision * recall) / (precision + recall + 1e-9)
    return precision, recall, f1
    