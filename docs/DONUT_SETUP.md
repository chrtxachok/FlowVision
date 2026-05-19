# Доступность и конфигурация Donut API

## 🚀 Быстрый старт

### 1. Локальное тестирование модели

```bash
# Загрузить и протестировать Donut локально (без HTTP)
python scripts/test_donut_api.py --path static/image.jpg --doc-type waybill

# Альтернативно, с GPU (если доступен CUDA)
python scripts/test_donut_api.py --path static/image.jpg --doc-type waybill --device cuda
```

### 2. Запуск API сервера

```bash
# Развернуть FastAPI сервер с Donut endpoints
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Проверить здоровье сервера
curl http://localhost:8000/health

# Получить информацию о модели
curl http://localhost:8000/api/v1/donut/info
```

### 3. Тестирование HTTP API

```bash
# Протестировать extraction через HTTP
python scripts/test_donut_http.py --path static/image.jpg --doc-type invoice

# Или вручную через curl
curl -X POST "http://localhost:8000/api/v1/donut/extract?document_type=waybill" \
  -F "file=@document.jpg"
```

---

## ⚙️ Конфигурация

### .env переменные

Создайте или отредактируйте файл `.env`:

```env
# === Donut Configuration ===

# Включить/отключить Donut
DONUT_ENABLED=true

# Название модели (HuggingFace hub или локальный путь)
# Доступные модели:
#   - naver-clova-ocr/donut-base (default, ~230 MB)
#   - naver-clova-ocr/donut-large (~500 MB)
#   - path/to/local/model
DONUT_MODEL_NAME=naver-clova-ocr/donut-base

# Директория для кэша моделей
DONUT_CACHE_DIR=./models

# Device: cpu или cuda (GPU требует CUDA и PyTorch with CUDA support)
DONUT_DEVICE=cpu

# Параметры генерации
DONUT_MAX_LENGTH=384      # Максимальная длина output
DONUT_NUM_BEAMS=1         # 1 = greedy decoding, >1 = beam search
DONUT_TEMPERATURE=1.0     # Температура для sampling

# === Основные настройки ===

API_KEY=dev-secret-key-change-in-production
DEBUG=false
LOG_LEVEL=INFO

# OCR backend (для других эндпоинтов)
OCR_BACKEND=easyocr
OCR_DEVICE=cpu

# === Ограничения ===

MAX_FILE_SIZE=10485760    # 10 MB в байтах
MAX_IMAGE_DIMENSION=4096
CONFIDENCE_THRESHOLD=0.7
```

### Загрузка конфигурации (PowerShell)

```powershell
# Загрузить переменные из .env
.\scripts\load_env.ps1

# Проверить конфигурацию
python -c "from app.config import settings; print(f'DONUT_ENABLED: {settings.DONUT_ENABLED}'); print(f'DONUT_MODEL_NAME: {settings.DONUT_MODEL_NAME}')"
```

---

## 📋 Структура API

### Основные endpoints

```
GET  /health                           — Проверка здоровья
POST /api/v1/donut/extract            — Извлечение данных из документа
GET  /api/v1/donut/info               — Информация о модели
POST /api/v1/donut/parse-json         — Парсинг JSON результата
```

---

## 🎯 Примеры использования

### Python (requests)

```python
import requests

api_url = "http://localhost:8000"
document_path = "path/to/document.jpg"

# Обработка документа
with open(document_path, 'rb') as f:
    response = requests.post(
        f"{api_url}/api/v1/donut/extract?document_type=invoice",
        files={'file': f},
        timeout=60
    )

if response.status_code == 200:
    result = response.json()
    print(f"Status: {result['status']}")
    print(f"Extracted: {result['extracted_data']}")
else:
    print(f"Error: {response.text}")
```

### JavaScript (Fetch API)

```javascript
async function extractDocument() {
    const formData = new FormData();
    const fileInput = document.getElementById('file-input');
    formData.append('file', fileInput.files[0]);
    
    const response = await fetch(
        'http://localhost:8000/api/v1/donut/extract?document_type=invoice',
        {
            method: 'POST',
            body: formData
        }
    );
    
    const result = await response.json();
    console.log(result.extracted_data);
}
```

### cURL

```bash
# Извлечение
curl -X POST "http://localhost:8000/api/v1/donut/extract?document_type=waybill" \
  -H "accept: application/json" \
  -F "file=@document.jpg"

# Информация о модели
curl -X GET "http://localhost:8000/api/v1/donut/info"
```

---

## 🐳 Docker

### Построение образа

```dockerfile
# Dockerfile с поддержкой Donut
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV DONUT_DEVICE=cpu
ENV DONUT_ENABLED=true

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  donut-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DONUT_ENABLED: "true"
      DONUT_DEVICE: "cpu"
      DONUT_MODEL_NAME: "naver-clova-ocr/donut-base"
      LOG_LEVEL: "INFO"
    volumes:
      - ./models:/app/models
      - ./logs:/app/logs
    restart: unless-stopped
```

### Запуск контейнера

```bash
# Сборка
docker build -t donut-api .

# Запуск
docker run -p 8000:8000 \
  -e DONUT_DEVICE=cpu \
  -v $(pwd)/models:/app/models \
  donut-api

# Или через docker-compose
docker-compose up -d
```

---

## 📊 Мониторинг и логирование

### Логирование

Логи выводятся в консоль и сохраняются в зависимости от конфигурации:

```python
# app/config.py
LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Примеры логов

```
INFO: Инициализирую Donut extractor...
INFO: Загружаем модель 'naver-clova-ocr/donut-base'...
INFO: ✓ Модель успешно загружена
INFO: Запускаю Donut для документа типа 'waybill'...
INFO: Donut extraction выполнен за 2.35s
```

---

## ⚠️ Trouble Shooting

### Проблема: "Module 'transformers' not found"

```bash
# Решение: установите transformers
pip install transformers>=4.30.0
```

### Проблема: "Model not found on HuggingFace"

```bash
# Решение 1: используйте зеркало
export HF_ENDPOINT=https://hf-mirror.com
python -c "from transformers import DonutProcessor; DonutProcessor.from_pretrained('naver-clova-ocr/donut-base')"

# Решение 2: скачайте модель локально
huggingface-cli download naver-clova-ocr/donut-base --local-dir ./models/donut-base
# Затем в .env: DONUT_MODEL_NAME=./models/donut-base
```

### Проблема: "CUDA out of memory"

```bash
# Решение: используйте CPU вместо GPU
DONUT_DEVICE=cpu

# Или уменьшите размер входного изображения в MAX_IMAGE_DIMENSION
```

### Проблема: "API timeout"

```bash
# Решение: увеличьте timeout в HTTP запросе
python scripts/test_donut_http.py --path document.jpg --timeout 120

# Или в коде
response = requests.post(url, ..., timeout=120)  # 120 секунд
```

---

## 📈 Производительность

### Бенчмарки (на одном документе)

| Device | Model | Load Time | Extraction Time | Total |
|--------|-------|-----------|-----------------|-------|
| CPU    | donut-base | 3.5s | 2.5s | 6.0s |
| GPU    | donut-base | 1.2s | 0.8s | 2.0s |
| GPU    | donut-large | 1.5s | 1.2s | 2.7s |

*Примерные значения на RTX 3090, могут отличаться в зависимости от оборудования.*

### Оптимизация

1. **Используйте GPU** для production (3-4x ускорение)
2. **Кэшируйте модель** (инициализируется один раз при старте)
3. **Батчируйте запросы** (обрабатывайте несколько документов параллельно)
4. **Используйте float16** на GPU (уменьшит памят)

---

## 📚 Дополнительные ресурсы

- [Donut Paper](https://arxiv.org/abs/2111.15664)
- [HuggingFace Model Card](https://huggingface.co/naver-clova-ocr/donut-base)
- [Transformers Documentation](https://huggingface.co/docs/transformers)
- [FlowVision Documentation](../readme.md)

---

## 🤝 Support

Вопросы и проблемы:

1. Проверьте [документацию API](./DONUT_API.md)
2. Посмотрите примеры в [scripts/](../scripts/)
3. Запустите тесты: `python scripts/test_donut_api.py --path static/image.jpg`
