# FlowLogix OCR Service FlowVision
Микросервис для распознавания накладных и других документов в логистике.

## 🚀 Возможности

- Распознавание русского языка
- Извлечение структурированных данных:
  - Номер накладной
  - Дата
  - Отправитель/получатель
  - Описание груза
  - Масса и сумма
- Поддержка форматов: JPEG, PNG, PDF
- Высокая точность (>85% для стандартных накладных)

## 📋 Требования

- Python 3.11+
- Docker (опционально)
- 2 ГБ оперативной памяти

## 🛠️ Установка

### Установка зависимостей

```bash
pip install -r requirements.txt
```

### Модели

- **EasyOCR (рекомендуется)**: модели скачиваются автоматически при первом запуске.
- **PaddleOCR (legacy)**: при `OCR_BACKEND=paddleocr` можно заранее скачать модели:

```bash
python scripts/download_models.py
```

### Настройка переменных окружения

```bash
copy .env.example .env
```

Дальше отредактируйте `.env` при необходимости.

### Тестирование (локальный smoke-test)

```bash
python scripts/test_ocr.py --path static/image.jpg --doc-type waybill
```

### Запуск API

```bash
uvicorn app.main:app --reload
```

## 🧠 Как работает программа (в целом)

Ниже описан основной синхронный “путь данных”, который используется и в `scripts/test_ocr.py`, и в API эндпоинте `app.main`.

1. **Вход**: байты файла + MIME-тип (`image/jpeg`, `image/png`, `application/pdf`) + `document_type` (например, `waybill`).
2. **Preprocess** (`app/ocr/preprocess.py`):
   - JPEG/PNG: декодирование через PIL → numpy → BGR (OpenCV-формат)
   - PDF: рендер первой страницы (PyMuPDF) → BGR
   - Улучшение изображения (`enhance_image`) для OCR
3. **OCR backend** (`app/ocr/pipeline.py`):
   - `easyocr` (по умолчанию): `Reader.readtext()` на RGB-изображении
   - `paddleocr` (legacy): `PaddleOCR.predict()` на BGR-изображении
4. **Postprocess** (`app/ocr/postprocess.py`):
   - Приведение raw-результата backend'а к единому формату:
     `{"full_text": str, "lines": [{"text","confidence","bbox"}], "blocks": [...] }`
5. **Processor** (`app/processors/*.py`):
   - Логика конкретного типа документа (например, `WaybillProcessor`) извлекает структурированные поля регулярками/эвристиками.
6. **Выход**: `OCRResponse` (`app/base_models/response.py`) со статусом, уверенностью, временем обработки и `extracted_data`.

## 🐳 Docker

```bash
docker-compose up -d
```

# 📡 API
Health Check

```bash
GET /health
```

Обработка документа

```bash
POST /api/v1/ocr/process
```

Форма:
- `file`: изображение или PDF
- `document_type`: `waybill|invoice|act|upd`