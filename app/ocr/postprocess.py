"""
Постобработка raw-результатов OCR backend'ов.

Поддерживаемые форматы:
  - PaddleOCR v3 (PaddleX backend): список объектов (по одному на изображение), каждый имеет .json()
  - EasyOCR: список элементов вида (bbox, text, confidence)

Структура res[i] (пример):
    {
        "input_path": "...",
        "page_index": null,
        "model_settings": {...},
        "dt_polys": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],  <- для каждой строки
        "text_det_params": {...},
        "text_type": "general",
        "textline_orientation_angles": [...],
        "text_rec_score": [...],
        "rec_text": [...],
        "rec_score": [...],         <- float confidence для каждой строки
        "input_img": ...
    }

Или формат полей может быть в списке:
    res.json() → {"res": [{"dt_polys": ..., "rec_text": ..., "rec_score": ...}, ...]}
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def parse_ocr_result(raw_results: List[Any]) -> Dict[str, Any]:
    """
    Преобразует raw-результат OCR backend'а в удобный словарь.

    Args:
        raw_results: список объектов из OCRPipeline.run(image)

    Returns:
        {
            "full_text": str,
            "lines": [{"text": str, "confidence": float, "bbox": [x1,y1,x2,y2]}, ...],
            "blocks": [str, ...]
        }

    Рationale (почему вообще нужна нормализация):
      - разные OCR движки возвращают разные структуры данных;
      - процессоры документов (`app/processors/*`) хотят работать с единым форматом;
      - этот модуль — единственная точка, где мы “знаем” про детали paddleocr/easyocr.
    """
    lines: List[Dict] = []

    if not raw_results:
        logger.warning("OCR вернул пустой результат")
        return {"full_text": "", "lines": [], "blocks": []}

    # EasyOCR: список (bbox, text, conf) по строкам
    if _looks_like_easyocr(raw_results):
        try:
            lines = _parse_easyocr_result(raw_results)
        except Exception as exc:
            logger.error("Не удалось распарсить результат EasyOCR: %s", exc)
            lines = []
        full_text = "\n".join(ln["text"] for ln in lines)
        blocks = [ln["text"] for ln in lines if ln["text"]]
        return {"full_text": full_text, "lines": lines, "blocks": blocks}

    # PaddleOCR v3: список результатов (по одному объекту на изображение).
    # Берём первый (мы всегда передаём одно изображение).
    result_obj = raw_results[0]

    try:
        lines = _parse_v3_result(result_obj)
    except Exception as exc:
        logger.error("Не удалось распарсить результат PaddleOCR v3: %s", exc)
        # Пробуем fallback: старый формат PaddleOCR v2
        try:
            lines = _parse_v2_result(result_obj)
        except Exception as exc2:
            logger.error("Fallback парсинг тоже не удался: %s", exc2)

    full_text = "\n".join(ln["text"] for ln in lines)
    blocks = [ln["text"] for ln in lines if ln["text"]]

    return {
        "full_text": full_text,
        "lines": lines,
        "blocks": blocks,
    }


# ------------------------------------------------------------------
# Парсеры форматов
# ------------------------------------------------------------------

def _looks_like_easyocr(raw_results: List[Any]) -> bool:
    """
    Дешёвая эвристика для EasyOCR:
    результат — это list[tuple/list] где каждый элемент похож на (bbox, text, conf).
    """
    if not isinstance(raw_results, list) or not raw_results:
        return False
    first = raw_results[0]
    if not isinstance(first, (list, tuple)) or len(first) != 3:
        return False
    bbox, text, conf = first
    if not isinstance(text, str):
        return False
    if not isinstance(conf, (float, int)):
        return False
    # bbox: обычно 4 точки
    return isinstance(bbox, (list, tuple)) and len(bbox) == 4


def _parse_easyocr_result(result_list: List[Any]) -> List[Dict]:
    """Парсит результат EasyOCR: [(bbox, text, conf), ...]."""
    lines: List[Dict] = []
    for item in result_list:
        if not item:
            continue
        try:
            bbox_pts, text, confidence = item
        except Exception:
            continue
        if not text:
            continue
        bbox = _polys_to_bbox(_normalize_points(bbox_pts))
        lines.append(
            {
                "text": str(text).strip(),
                "confidence": round(float(confidence), 4),
                "bbox": bbox,
            }
        )
    return lines


def _parse_v3_result(result_obj: Any) -> List[Dict]:
    """Парсит объект результата PaddleOCR v3 (PaddleX backend)."""
    lines = []

    # Пробуем получить данные через .json() → dict
    if hasattr(result_obj, "json"):
        data = result_obj.json()
    elif isinstance(result_obj, dict):
        data = result_obj
    else:
        # Объект может быть итерируемым (список строк)
        data = None

    if data is not None:
        # Формат 1: {"res": [{...}, ...]}
        res_list = data.get("res", [])
        if isinstance(res_list, list) and res_list:
            for item in res_list:
                text = item.get("rec_text", "")
                score = float(item.get("rec_score", 0.0))
                polys = item.get("dt_polys", [])
                bbox = _polys_to_bbox(polys)
                if text:
                    lines.append({"text": text.strip(), "confidence": round(score, 4), "bbox": bbox})
            return lines

        # Формат 2: плоский объект с параллельными списками
        rec_texts = data.get("rec_text", [])
        rec_scores = data.get("rec_score", [])
        dt_polys = data.get("dt_polys", [])

        if rec_texts:
            for i, text in enumerate(rec_texts):
                score = float(rec_scores[i]) if i < len(rec_scores) else 0.0
                polys = dt_polys[i] if i < len(dt_polys) else []
                bbox = _polys_to_bbox(polys)
                if text:
                    lines.append({"text": text.strip(), "confidence": round(score, 4), "bbox": bbox})
            return lines

    # Формат 3: итерируемый объект
    for item in result_obj:
        if item is None:
            continue
        if isinstance(item, dict):
            text = item.get("rec_text", "")
            score = float(item.get("rec_score", 0.0))
            polys = item.get("dt_polys", [])
        else:
            # Старый fallback к v2 формату [[bbox, (text, conf)]]
            return _parse_v2_result(result_obj)
        bbox = _polys_to_bbox(polys)
        if text:
            lines.append({"text": text.strip(), "confidence": round(score, 4), "bbox": bbox})

    return lines


def _parse_v2_result(result_obj: Any) -> List[Dict]:
    """
    Fallback парсинг для старого формата PaddleOCR v2:
    [[[[x1,y1],[x2,y2],[x3,y3],[x4,y4]], ("text", conf)], ...]
    """
    lines = []
    page = result_obj[0] if (isinstance(result_obj, (list, tuple)) and result_obj) else result_obj
    if not page:
        return lines
    for item in page:
        if item is None:
            continue
        try:
            bbox_pts, (text, confidence) = item
            xs = [pt[0] for pt in bbox_pts]
            ys = [pt[1] for pt in bbox_pts]
            bbox = [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]
            lines.append({"text": text.strip(), "confidence": round(float(confidence), 4), "bbox": bbox})
        except Exception as exc:
            logger.debug("Не удалось распарсить строку: %s — %s", item, exc)
    return lines


def _polys_to_bbox(polys: List) -> List[int]:
    """Конвертирует полигон в axis-aligned bounding box [x1, y1, x2, y2]."""
    if not polys:
        return [0, 0, 0, 0]
    try:
        xs = [pt[0] for pt in polys]
        ys = [pt[1] for pt in polys]
        return [int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))]
    except Exception:
        return [0, 0, 0, 0]


def _normalize_points(polys: Any) -> List[List[float]]:
    """
    EasyOCR может возвращать точки как numpy arrays / tuples.
    Приводим к списку точек [[x,y], ...].
    """
    if polys is None:
        return []
    pts: List[List[float]] = []
    for pt in polys:
        try:
            x, y = pt
            pts.append([float(x), float(y)])
        except Exception:
            continue
    return pts
