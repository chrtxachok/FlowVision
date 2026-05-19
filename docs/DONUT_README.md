# 🍩 Donut API Integration

Полная интеграция модели **Donut** (Document Understanding Transformer) в FlowVision OCR микросервис.

## 📦 Что включено

### Core Components

- **[DonutExtractor](../app/ocr/donut_extractor.py)** — класс для работы с Donut моделью
  - Загрузка предобученных моделей с HuggingFace
  - Поддержка GPU/CPU
  - Извлечение структурированных данных из документов

### API Endpoints

- **[donut_routes.py](../app/api/donut_routes.py)** — REST API для Donut
  - `POST /api/v1/donut/extract` — обработка документа
  - `GET /api/v1/donut/info` — информация о модели
  - `POST /api/v1/donut/parse-json` — парсинг результатов

### Document Processors

- **[DonutProcessor](../app/processors/donut.py)** — процессор для структурированного извлечения
  - Парсинг JSON результатов Donut
  - Нормализация полей документа
  - Интеграция с существующей системой процессоров

### Testing Scripts

- **[test_donut_api.py](../scripts/test_donut_api.py)** — локальное тестирование
- **[test_donut_http.py](../scripts/test_donut_http.py)** — тестирование HTTP API

### Documentation

- **[DONUT_API.md](./DONUT_API.md)** — полная документация API
- **[DONUT_SETUP.md](./DONUT_SETUP.md)** — инструкции по настройке

---

## 🚀 Быстрый старт

### 1. Установка

```bash
# Зависимости уже в requirements.txt (transformers, torch)
pip install -r requirements.txt
```

### 2. Конфигурация

Создайте или отредактируйте `.env`:

```env
DONUT_ENABLED=true
DONUT_MODEL_NAME=naver-clova-ocr/donut-base
DONUT_DEVICE=cpu  # или cuda
```

### 3. Запуск

```bash
# Локальное тестирование
python scripts/test_donut_api.py --path static/image.jpg --doc-type waybill

# API сервер
uvicorn app.main:app --reload

# HTTP тестирование
python scripts/test_donut_http.py --path static/image.jpg --doc-type invoice
```

---

## 📋 API Usage

### Извлечение данных

```bash
curl -X POST "http://localhost:8000/api/v1/donut/extract?document_type=waybill" \
  -F "file=@document.jpg"
```

### Информация о модели

```bash
curl http://localhost:8000/api/v1/donut/info
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│         FastAPI Application             │
│  (app.main)                             │
└──────────────┬──────────────────────────┘
               │
        ┌──────┴───────┐
        │              │
        v              v
  ┌──────────┐   ┌────────────────┐
  │ OCR API  │   │ Donut API      │
  │ (old)    │   │ (new)          │
  └──────────┘   │                │
                 │ donut_routes.py│
                 └────────┬────────┘
                          │
                    ┌─────v─────┐
                    │ Donut     │
                    │ Extractor │
                    │(HF models)│
                    └─────┬─────┘
                          │
            ┌─────────────┴─────────────┐
            │                           │
       ┌────v─────┐           ┌────────v──────┐
       │ Preprocess│           │ Post-process  │
       │(bytes→img)│           │(parse JSON)  │
       └──────────┘           └───────────────┘
```

---

## 🔧 Components

### DonutExtractor

```python
from app.ocr.donut_extractor import DonutExtractor

# Инициализация
extractor = DonutExtractor.from_pretrained(
    model_name_or_path="naver-clova-ocr/donut-base",
    device="cpu"
)

# Использование
result = extractor.extract(
    image=image_array,
    task_prompt="<s_invoice>"
)

# Результат
{
    "text": "{...JSON...}",
    "confidence": 0.95,
    "metadata": {...}
}
```

### API Endpoint

```python
@router.post("/api/v1/donut/extract")
async def extract_with_donut(
    file: UploadFile,
    document_type: str,
    extractor: DonutExtractor = Depends(get_donut_extractor)
) -> OCRResponse:
    # Загрузка файла → Donut → JSON парсинг → Ответ
    ...
```

### Document Processor

```python
from app.processors.donut import DonutProcessor

processor = DonutProcessor()
result = processor.process(donut_result, image_type="image/jpeg")

# Нормализованные данные:
{
    "waybill_number": {"value": "ТТН001", "confidence": 0.95},
    "date": {"value": "2024-05-14", "confidence": 0.98},
    ...
}
```

---

## 📊 Supported Document Types

| Type | Task Prompt | Example |
|------|-------------|---------|
| Invoice | `<s_invoice>` | Счета-фактуры |
| Waybill | `<s_waybill>` | Накладные (ТТН) |
| Act | `<s_act>` | Акты выполненных работ |
| UPD | `<s_upd>` | Универсальные передаточные документы |

---

## ⚡ Performance

| Metric | Value |
|--------|-------|
| Model Size | ~230 MB (donut-base) |
| Load Time (CPU) | ~3-4s |
| Extraction Time (CPU) | ~2-3s per document |
| Load Time (GPU) | ~1-2s |
| Extraction Time (GPU) | ~0.5-1s per document |
| Memory (CPU) | ~1.5 GB |
| Memory (GPU) | ~2-4 GB |

---

## 🔌 Integration Points

### Existing OCRService

```python
# Можно использовать вместе с существующим OCR
class OCRService:
    def __init__(self):
        self._pipeline = OCRPipeline()  # easyocr/paddleocr
        self._donut = DonutExtractor.from_pretrained()  # NEW
    
    async def process_document(self, file_bytes, file_type, doc_type, use_donut=False):
        if use_donut:
            return await self._process_with_donut(...)
        else:
            return await self._process_with_ocr(...)
```

### Response Format

```python
OCRResponse(
    status=ProcessingStatus.SUCCESS,
    document_type="invoice",
    confidence=0.95,
    processing_time_ms=2350,
    extracted_data={...},
    raw_text="<s_invoice>...",
    metadata={"model_type": "donut"}
)
```

---

## 🐛 Debugging

### Enable verbose logging

```python
# app/config.py
LOG_LEVEL = "DEBUG"
```

### Local testing with debug output

```bash
python scripts/test_donut_api.py --path document.jpg --doc-type invoice
```

### Check model loading

```python
python -c "
from app.ocr.donut_extractor import DonutExtractor
extractor = DonutExtractor.from_pretrained()
print(f'Model: {extractor.model_path}')
print(f'Device: {extractor.device}')
"
```

---

## 🚀 Production Deployment

### Docker

```bash
docker build -t donut-api .
docker run -p 8000:8000 \
  -e DONUT_DEVICE=cuda \
  -v $(pwd)/models:/app/models \
  donut-api
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: donut-api
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: donut-api
        image: donut-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DONUT_DEVICE
          value: "cuda"
        resources:
          requests:
            memory: "2Gi"
            nvidia.com/gpu: "1"
          limits:
            memory: "4Gi"
            nvidia.com/gpu: "1"
```

### Scaling

- **Горизонтальное масштабирование**: используйте несколько инстансов API
- **Батчинг**: накапливайте документы для параллельной обработки
- **Кэширование**: кэшируйте результаты часто запрашиваемых документов

---

## 📚 Documentation

- **[DONUT_API.md](./DONUT_API.md)** — полная документация REST API
- **[DONUT_SETUP.md](./DONUT_SETUP.md)** — инструкции по конфигурации
- **[Donut Paper](https://arxiv.org/abs/2111.15664)** — научная статья

---

## 🤝 Support & Contribution

### Issues

Если встречаетесь с проблемами:

1. Проверьте [DONUT_SETUP.md](./DONUT_SETUP.md#-trouble-shooting)
2. Запустите тестовый скрипт с verbose логированием
3. Проверьте версии зависимостей

### Contributing

Приветствуются улучшения:

- Fine-tuned модели для специфичных типов документов
- Поддержка дополнительных output форматов
- Оптимизация производительности
- Расширение документации

---

## 📝 Files Structure

```
FlowVision/
├── app/
│   ├── ocr/
│   │   └── donut_extractor.py          # Core Donut класс
│   ├── api/
│   │   └── donut_routes.py             # REST endpoints
│   ├── processors/
│   │   └── donut.py                    # Document processor
│   └── config.py                       # Donut settings
├── scripts/
│   ├── test_donut_api.py               # Local testing
│   └── test_donut_http.py              # HTTP testing
├── docs/
│   ├── DONUT_API.md                    # API reference
│   ├── DONUT_SETUP.md                  # Setup guide
│   └── DONUT_README.md                 # This file
└── requirements.txt
```

---

## 📄 License

- **Donut Model**: Apache 2.0
- **Transformers**: Apache 2.0
- **FlowVision**: [Your License]

---

**Last Updated**: 2024-05-14  
**Status**: ✅ Production Ready
