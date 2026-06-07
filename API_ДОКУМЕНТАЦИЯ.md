# 📚 API Документация FlowLogix OCR Service

## Содержание
- [Общая информация](#общая-информация)
- [Аутентификация](#аутентификация)
- [Эндпоинты](#эндпоинты)
- [Примеры запросов](#примеры-запросов)
- [Коды ошибок](#коды-ошибок)
- [Rate Limiting](#rate-limiting)
- [Best Practices](#best-practices)

---

## Общая информация

### Base URL
```
http://localhost:8000
```

### API Version
```
v1
```

### Content-Type
```
multipart/form-data (для загрузки файлов)
application/json (для ответов)
```

### Response Format
Все ответы возвращаются в формате JSON

---

## Аутентификация

### API Key Authentication

Все запросы к защищенным эндпоинтам требуют API ключ.

**Способы передачи API ключа:**

1. **Через query parameter:**
```
POST /api/v1/ocr/process?api_key=dev-secret-key-change-in-production
```

2. **Через form data (для multipart):**
```
POST /api/v1/ocr/process
Content-Type: multipart/form-data

api_key=dev-secret-key-change-in-production
file=<binary data>
```

3. **Через header (альтернативно):**
```
POST /api/v1/ocr/process
X-API-Key: dev-secret-key-change-in-production
```

### Получить/изменить API ключ

**Default:** `dev-secret-key-change-in-production`

**Изменить в `.env`:**
```env
API_KEY=your-secret-key-here
```

**В продакшене:**
- Генерируйте сильные ключи (UUID v4)
- Храните в переменных окружения, НЕ в коде
- Ротируйте ключи регулярно
- Используйте HTTPS (не HTTP)

---

## Эндпоинты

### 1️⃣ Главная страница (Web UI)

#### GET /

**Описание:** Возвращает веб-интерфейс для загрузки и обработки документов

**Параметры:** -

**Ответ:**
- **200 OK** - HTML страница со стилями и JavaScript

**Пример:**
```bash
curl http://localhost:8000/ --output index.html
open index.html
```

---

### 2️⃣ Основной эндпоинт OCR

#### POST /api/v1/ocr/process

**Описание:** Главный эндпоинт для обработки документов. Загружает файл, распознает текст и извлекает структурированные данные.

**Request Format:** `multipart/form-data`

**Параметры запроса:**

| Параметр | Тип | Обязательный | По умолчанию | Описание |
|----------|-----|--------------|----------------|------------|
| `file` | File | ✅ Да | - | Файл документа (JPG/PNG/PDF) |
| `document_type` | String | ❌ Нет | `waybill` | Тип документа: `waybill`, `invoice`, `act`, `upd` |
| `api_key` | String | ❌ Нет | (из .env) | API ключ для аутентификации |

**Ограничения файла:**
- **Максимальный размер:** 10 МБ
- **Поддерживаемые форматы:** 
  - `image/jpeg` (.jpg, .jpeg)
  - `image/png` (.png)
  - `application/pdf` (.pdf)
- **Разрешение:** до 4096x4096 пиксели

**Response: 200 OK**

```json
{
  "status": "success",
  "document_type": "waybill",
  "confidence": 0.87,
  "processing_time_ms": 2450,
  "extracted_data": {
    "waybill_number": {
      "value": "ТТН-2024-001",
      "confidence": 0.95,
      "bbox": [10, 20, 100, 40],
      "raw_text": "Накладная № ТТН-2024-001"
    },
    "date": {
      "value": "01.06.2024",
      "confidence": 0.92,
      "bbox": [10, 50, 100, 70],
      "raw_text": "от 01.06.2024"
    },
    "sender": {
      "value": "ООО СервисЛогистика",
      "confidence": 0.88,
      "bbox": [10, 100, 200, 120],
      "raw_text": "Отправитель: ООО СервисЛогистика"
    },
    "recipient": {
      "value": "ИП Иванов И.И.",
      "confidence": 0.85,
      "bbox": [10, 150, 150, 170],
      "raw_text": "Получатель: ИП Иванов И.И."
    },
    "cargo_description": {
      "value": "Электроника, товары в коробках",
      "confidence": 0.80,
      "bbox": [10, 200, 300, 220],
      "raw_text": "Груз: Электроника, товары в коробках"
    },
    "cargo_mass_kg": {
      "value": "45.5",
      "confidence": 0.90,
      "bbox": [10, 250, 80, 270],
      "raw_text": "Масса: 45.5 кг"
    },
    "total_amount": {
      "value": "15000.00",
      "confidence": 0.91,
      "bbox": [10, 300, 100, 320],
      "raw_text": "Итого: 15000.00 руб"
    },
    "driver_name": {
      "value": "Сидоров Петр",
      "confidence": 0.75,
      "bbox": [10, 350, 150, 370],
      "raw_text": "Водитель: Сидоров Петр"
    },
    "vehicle_number": {
      "value": "А123БВ77",
      "confidence": 0.93,
      "bbox": [10, 400, 100, 420],
      "raw_text": "А123БВ77"
    }
  },
  "raw_text": "Накладная № ТТН-2024-001\nОт 01.06.2024\n...\nА123БВ77",
  "warnings": [],
  "metadata": {
    "lines_detected": 24,
    "file_type": "image/jpeg",
    "ocr_backend": "easyocr"
  }
}
```

**Response: 400 Bad Request**

```json
{
  "error": "unsupported_file_type",
  "message": "Unsupported file type. Supported: image/jpeg, image/png, application/pdf",
  "details": {
    "received": "image/webp",
    "supported": ["image/jpeg", "image/png", "application/pdf"]
  }
}
```

```json
{
  "error": "file_too_large",
  "message": "File too large (max 10 MB). Received: 15 MB",
  "details": {
    "max_size_mb": 10,
    "received_size_mb": 15
  }
}
```

**Response: 401 Unauthorized**

```json
{
  "error": "invalid_api_key",
  "message": "Invalid API key",
  "details": null
}
```

**Response: 500 Internal Server Error**

```json
{
  "error": "ocr_processing_failed",
  "message": "Failed to initialize EasyOCR: CUDA device not found",
  "details": {
    "backend": "easyocr",
    "stage": "ocr_recognition"
  }
}
```

---

### 3️⃣ Информация о сервисе

#### GET /api/v1/ocr/info

**Описание:** Получить информацию о поддерживаемых типах документов, форматах и ограничениях сервиса

**Параметры:** -

**Response: 200 OK**

```json
{
  "supported_types": [
    "waybill",
    "invoice",
    "act",
    "upd"
  ],
  "supported_formats": [
    "image/jpeg",
    "image/png",
    "application/pdf"
  ],
  "max_file_size_mb": 10,
  "version": "1.0.0"
}
```

---

### 4️⃣ Health Check

#### GET /health

**Описание:** Проверить состояние сервиса

**Параметры:** -

**Response: 200 OK**

```json
{
  "status": "healthy",
  "service": "ocr"
}
```

**Response: 503 Service Unavailable** (если сервис недоступен)

```json
{
  "status": "unhealthy",
  "service": "ocr",
  "error": "OCR model not loaded"
}
```

---

### 5️⃣ Документация API (Swagger/OpenAPI)

#### GET /docs

**Описание:** Интерактивная документация API (Swagger UI)

**Параметры:** -

**Response:** HTML страница с интерактивным тестировщиком API

---

#### GET /redoc

**Описание:** Альтернативная документация API (ReDoc)

**Параметры:** -

**Response:** HTML страница с красивой документацией

---

## Примеры запросов

### Пример 1: cURL - Базовая накладная

```bash
curl -X POST http://localhost:8000/api/v1/ocr/process \
  -F "file=@waybill.jpg" \
  -F "document_type=waybill" \
  -F "api_key=dev-secret-key-change-in-production" \
  | python -m json.tool
```

### Пример 2: cURL - Счет-фактура с PDF

```bash
curl -X POST http://localhost:8000/api/v1/ocr/process \
  -F "file=@invoice.pdf" \
  -F "document_type=invoice" \
  -F "api_key=dev-secret-key-change-in-production" \
  -o response.json
```

### Пример 3: Python Requests

```python
import requests
import json

# Загружаем и обрабатываем накладную
with open('document.png', 'rb') as f:
    files = {
        'file': f
    }
    data = {
        'document_type': 'waybill',
        'api_key': 'dev-secret-key-change-in-production'
    }
    
    response = requests.post(
        'http://localhost:8000/api/v1/ocr/process',
        files=files,
        data=data,
        timeout=120  # 2 минуты
    )

# Проверяем результат
if response.status_code == 200:
    result = response.json()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # Доступ к извлеченным данным
    waybill_number = result['extracted_data']['waybill_number']['value']
    print(f"\n📋 Номер накладной: {waybill_number}")
    
    # Получить общую точность
    confidence = result['confidence']
    print(f"📊 Точность распознавания: {confidence:.1%}")
    
    # Время обработки
    time_ms = result['processing_time_ms']
    print(f"⏱️  Время обработки: {time_ms}ms")
else:
    error = response.json()
    print(f"❌ Ошибка {response.status_code}: {error['message']}")
```

### Пример 4: JavaScript Fetch API

```javascript
// Асинхронная функция для загрузки и обработки
async function processDocument(file) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', 'waybill');
    formData.append('api_key', 'dev-secret-key-change-in-production');
    
    try {
        const response = await fetch('/api/v1/ocr/process', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(`${response.status}: ${error.message}`);
        }
        
        const result = await response.json();
        
        // Использование результатов
        console.log('✓ Успешно обработано');
        console.log('📋 Извлеченные данные:', result.extracted_data);
        console.log('📊 Точность:', (result.confidence * 100).toFixed(1) + '%');
        console.log('⏱️  Время:', result.processing_time_ms + 'ms');
        
        return result;
        
    } catch (error) {
        console.error('❌ Ошибка:', error.message);
        throw error;
    }
}

// Использование
document.querySelector('input[type="file"]').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    try {
        const result = await processDocument(file);
        // Показать результаты в UI
        displayResults(result);
    } catch (error) {
        showError(error.message);
    }
});
```

### Пример 5: Python - Batch Processing

```python
import requests
import os
from pathlib import Path

def process_directory(directory_path, document_type='waybill'):
    """Обработать все документы в директории"""
    
    api_url = 'http://localhost:8000/api/v1/ocr/process'
    api_key = 'dev-secret-key-change-in-production'
    
    results = []
    files = Path(directory_path).glob('*.{jpg,jpeg,png,pdf}')
    
    for file_path in files:
        print(f"Обработка: {file_path.name}...", end=' ')
        
        try:
            with open(file_path, 'rb') as f:
                response = requests.post(
                    api_url,
                    files={'file': f},
                    data={
                        'document_type': document_type,
                        'api_key': api_key
                    },
                    timeout=120
                )
            
            if response.status_code == 200:
                result = response.json()
                results.append({
                    'filename': file_path.name,
                    'status': 'success',
                    'data': result['extracted_data'],
                    'confidence': result['confidence']
                })
                print(f"✓ {result['confidence']:.0%}")
            else:
                error = response.json()
                results.append({
                    'filename': file_path.name,
                    'status': 'error',
                    'error': error['message']
                })
                print(f"✗ {error['error']}")
        
        except Exception as e:
            results.append({
                'filename': file_path.name,
                'status': 'exception',
                'error': str(e)
            })
            print(f"✗ {e}")
    
    return results

# Использование
results = process_directory('./documents', document_type='waybill')

# Сохраняем результаты
import json
with open('results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\n✓ Обработано: {len(results)} документов")
print(f"✓ Успешно: {sum(1 for r in results if r['status'] == 'success')}")
print(f"✗ Ошибок: {sum(1 for r in results if r['status'] != 'success')}")
```

### Пример 6: Node.js - Express Integration

```javascript
const express = require('express');
const FormData = require('form-data');
const fs = require('fs');
const axios = require('axios');

const app = express();

// Middleware для обработки файлов
app.post('/upload', async (req, res) => {
    try {
        const file = req.files.document;
        
        // Создаем FormData для отправки на OCR API
        const form = new FormData();
        form.append('file', fs.createReadStream(file.tempFilePath));
        form.append('document_type', req.body.documentType || 'waybill');
        form.append('api_key', process.env.OCR_API_KEY);
        
        // Отправляем на OCR сервис
        const ocrResponse = await axios.post(
            'http://localhost:8000/api/v1/ocr/process',
            form,
            { headers: form.getHeaders() }
        );
        
        // Возвращаем результат
        res.json(ocrResponse.data);
        
    } catch (error) {
        console.error('OCR Error:', error.message);
        res.status(500).json({
            error: 'ocr_failed',
            message: error.message
        });
    }
});

app.listen(3000, () => {
    console.log('Server running on port 3000');
});
```

---

## Коды ошибок

| Код | Ошибка | Описание | Решение |
|-----|--------|---------|---------|
| **400** | `unsupported_file_type` | Неподдерживаемый формат файла | Используйте JPG, PNG или PDF |
| **400** | `file_too_large` | Файл превышает 10 МБ | Сжимите изображение |
| **400** | `invalid_document_type` | Неизвестный тип документа | Используйте: waybill, invoice, act, upd |
| **401** | `invalid_api_key` | Неверный API ключ | Проверьте `api_key` в .env |
| **403** | `access_denied` | Доступ запрещен | Связитесь с администратором |
| **413** | `payload_too_large` | Размер запроса слишком большой | Уменьшите размер файла |
| **429** | `rate_limit_exceeded` | Слишком много запросов | Ожидайте перед следующим запросом |
| **500** | `ocr_processing_failed` | Ошибка при распознавании | Проверьте логи сервера |
| **500** | `model_load_error` | Не удалось загрузить модель | Перезагрузите сервис |
| **503** | `service_unavailable` | Сервис недоступен | Проверьте статус сервера |

---

## Rate Limiting

### Текущие ограничения (по умолчанию):

- **Без ограничений** в dev режиме
- **На продакшене** рекомендуется:
  - 100 запросов в час per API key
  - 1000 запросов в день per API key

### Headers ответа (при включенном rate limiting):

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 2024-06-07T10:30:00Z
```

### Пример обработки rate limit:

```python
import time
import requests

def robust_ocr_request(file_path, max_retries=3):
    """Отправить запрос с обработкой rate limit"""
    
    for attempt in range(max_retries):
        try:
            with open(file_path, 'rb') as f:
                response = requests.post(
                    'http://localhost:8000/api/v1/ocr/process',
                    files={'file': f},
                    data={'api_key': 'your-key'},
                    timeout=120
                )
            
            if response.status_code == 429:  # Rate limited
                # Читаем время сброса
                reset_time = response.headers.get('X-RateLimit-Reset')
                print(f"⏳ Rate limited. Reset at: {reset_time}")
                time.sleep(60)  # Ждем минуту
                continue
            
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.Timeout:
            print(f"⏱️  Timeout на попытке {attempt + 1}")
            if attempt < max_retries - 1:
                time.sleep(5 * (attempt + 1))  # Exponential backoff
    
    raise Exception("Не удалось отправить запрос после нескольких попыток")
```

---

## Best Practices

### ✅ Рекомендации

1. **Используйте HTTPS в продакшене**
   ```
   https://api.yourdomain.com/api/v1/ocr/process
   ```

2. **Сохраняйте API ключ безопасно**
   ```python
   # ✓ Правильно
   api_key = os.environ.get('OCR_API_KEY')
   
   # ✗ Неправильно
   api_key = "dev-secret-key-change-in-production"  # в коде!
   ```

3. **Устанавливайте timeout**
   ```python
   response = requests.post(
       url,
       files=files,
       timeout=120  # 2 минуты
   )
   ```

4. **Обрабатывайте ошибки**
   ```python
   if response.status_code != 200:
       error = response.json()
       logger.error(f"OCR Error: {error['error']}")
       # Предпринимайте действия
   ```

5. **Логируйте результаты**
   ```python
   result = response.json()
   logger.info(f"Document processed. Confidence: {result['confidence']:.1%}")
   ```

### ❌ Антипаттерны

1. ❌ Не отправляйте очень больших файлов
   ```python
   # Сжимайте перед отправкой
   if file_size > 5 * 1024 * 1024:  # 5 МБ
       compress_image(file_path)
   ```

2. ❌ Не игнорируйте ошибки
   ```python
   # Плохо
   result = requests.post(url, files=files).json()
   
   # Хорошо
   response = requests.post(url, files=files)
   if response.status_code == 200:
       result = response.json()
   ```

3. ❌ Не переиспользуйте session без проверки
   ```python
   # Плохо: session может потеряться
   session.post(url)
   
   # Хорошо: новая сессия для каждого запроса
   response = requests.post(url)
   ```

4. ❌ Не отправляйте API ключ в URL
   ```python
   # ✗ Плохо (видно в логах)
   f"http://api.example.com?api_key={key}"
   
   # ✓ Хорошо (в header или form data)
   requests.post(url, data={'api_key': key})
   ```

---

## WebSocket API (Future)

Планируется добавление WebSocket для real-time обработки:

```javascript
// Планируется в v1.1
const ws = new WebSocket('ws://localhost:8000/api/v1/ocr/stream');

ws.onmessage = (event) => {
    const progress = JSON.parse(event.data);
    console.log(`Progress: ${progress.percent}%`);
};

ws.send(JSON.stringify({
    file: file,
    document_type: 'waybill'
}));
```

---

## Changelog API

### v1.0.0 (Current)
- ✓ POST /api/v1/ocr/process (основной эндпоинт)
- ✓ GET /api/v1/ocr/info (информация о сервисе)
- ✓ GET /health (health check)

### v1.1.0 (Planned)
- 🔄 WebSocket для real-time обработки
- 🔄 Batch API для множественной обработки
- 🔄 Async callbacks для webhooks

### v2.0.0 (Future)
- 🔄 Machine Learning для поля extraction
- 🔄 Таблицы и сложные структуры
- 🔄 Поддержка 10+ языков

