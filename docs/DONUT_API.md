# Donut API Documentation

## Обзор

Donut (Document Understanding Transformer) — это модель computer vision для end-to-end распознавания и структурированного извлечения данных из документов (накладные, счета, акты и т.д.).

В отличие от стандартного OCR пайплайна (обнаружение текста → распознавание), Donut работает с документом целиком и выводит структурированные данные.

## API Endpoints

### 1. Извлечение данных (синхронно)

**POST** `/api/v1/donut/extract`

Основной эндпоинт для обработки документа.

#### Параметры:

```
Content-Type: multipart/form-data

file: <binary> — Файл документа (JPEG, PNG, PDF)
document_type: string (query) — Тип документа
  Допустимые значения: waybill, invoice, act, upd
  По умолчанию: invoice
```

#### Пример запроса (curl):

```bash
curl -X POST "http://localhost:8000/api/v1/donut/extract?document_type=waybill" \
  -H "accept: application/json" \
  -F "file=@document.jpg"
```

#### Пример успешного ответа (200 OK):

```json
{
  "status": "success",
  "document_type": "waybill",
  "confidence": 0.95,
  "processing_time_ms": 2350,
  "extracted_data": {
    "waybill_number": "ТТН001234",
    "date": "2024-05-14",
    "sender": "ООО \"Логистика\"",
    "recipient": "ПАО \"Транспорт\"",
    "cargo_description": "Мебель",
    "cargo_mass_kg": 150,
    "total_amount": 5000.00,
    "driver_name": "Иван Петров",
    "vehicle_number": "А123БВ77"
  },
  "raw_text": "<s_waybill>...(full JSON from model)...</s_waybill>",
  "metadata": {
    "model": "naver-clova-ocr/donut-base",
    "model_type": "donut",
    "file_name": "document.jpg"
  }
}
```

#### Коды ошибок:

- **400 Bad Request** — Неподдерживаемый формат файла или файл повреждён
- **413 Payload Too Large** — Файл превышает максимальный размер (10 МБ)
- **500 Internal Server Error** — Ошибка при обработке

### 2. Информация о модели

**GET** `/api/v1/donut/info`

Получить информацию о загруженной Donut модели.

#### Пример запроса:

```bash
curl -X GET "http://localhost:8000/api/v1/donut/info"
```

#### Пример ответа:

```json
{
  "model": "naver-clova-ocr/donut-base",
  "device": "cpu",
  "task_prompt_default": "<s_invoice>",
  "supported_document_types": [
    "waybill",
    "invoice",
    "act",
    "upd"
  ],
  "generation_params": {
    "max_length": 384,
    "num_beams": 1,
    "temperature": 1.0
  },
  "supported_formats": [
    "image/jpeg",
    "image/png",
    "application/pdf"
  ],
  "max_file_size_mb": 10.0
}
```

### 3. Парсинг JSON результата

**POST** `/api/v1/donut/parse-json`

Парсит JSON результат Donut без повторного выполнения модели (полезно для тестирования).

#### Параметры:

```
raw_output: string (query) — Сырой output от Donut модели
document_type: string (query) — Тип документа
```

#### Пример запроса:

```bash
curl -X POST "http://localhost:8000/api/v1/donut/parse-json?document_type=invoice&raw_output=%7B%22invoice_number%22%3A%22001%22%7D"
```

#### Пример ответа:

```json
{
  "success": true,
  "document_type": "invoice",
  "extracted_data": {
    "invoice_number": "001"
  }
}
```

---

## Примеры использования

### Python (requests)

```python
import requests

# 1. Инициализация
BASE_URL = "http://localhost:8000"
DOCUMENT_PATH = "path/to/document.jpg"

# 2. Загрузка и обработка
with open(DOCUMENT_PATH, 'rb') as f:
    files = {'file': f}
    params = {'document_type': 'waybill'}
    
    response = requests.post(
        f"{BASE_URL}/api/v1/donut/extract",
        files=files,
        params=params
    )

# 3. Обработка результата
if response.status_code == 200:
    result = response.json()
    print(f"Status: {result['status']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Processing time: {result['processing_time_ms']}ms")
    print(f"Extracted data: {result['extracted_data']}")
else:
    print(f"Error: {response.status_code}")
    print(response.text)
```

### Python (async с httpx)

```python
import httpx
import asyncio

async def extract_document():
    async with httpx.AsyncClient() as client:
        with open("document.jpg", 'rb') as f:
            files = {'file': (f.name, f, 'image/jpeg')}
            params = {'document_type': 'invoice'}
            
            response = await client.post(
                "http://localhost:8000/api/v1/donut/extract",
                files=files,
                params=params,
                timeout=30.0
            )
            
            return response.json()

# Использование
result = asyncio.run(extract_document())
print(result['extracted_data'])
```

### JavaScript (fetch)

```javascript
async function extractDocument(filePath, documentType = 'waybill') {
    const formData = new FormData();
    const file = document.getElementById('file-input').files[0];
    formData.append('file', file);
    
    const response = await fetch(
        `http://localhost:8000/api/v1/donut/extract?document_type=${documentType}`,
        {
            method: 'POST',
            body: formData
        }
    );
    
    if (response.ok) {
        const result = await response.json();
        console.log('Extracted data:', result.extracted_data);
        console.log('Processing time:', result.processing_time_ms, 'ms');
        return result;
    } else {
        console.error('Error:', response.statusText);
    }
}
```

### cURL

```bash
# Обработка документа
curl -X POST "http://localhost:8000/api/v1/donut/extract?document_type=waybill" \
  -H "accept: application/json" \
  -F "file=@invoice.jpg"

# Получение информации о модели
curl -X GET "http://localhost:8000/api/v1/donut/info"

# Парсинг JSON результата
curl -X POST "http://localhost:8000/api/v1/donut/parse-json" \
  -H "accept: application/json" \
  -G \
  --data-urlencode 'raw_output={"invoice_number":"001"}' \
  --data-urlencode 'document_type=invoice'
```

---

## Конфигурация

### Переменные окружения (.env)

```env
# Включение Donut
DONUT_ENABLED=true

# Название модели (HuggingFace hub или локальный путь)
DONUT_MODEL_NAME=naver-clova-ocr/donut-base

# Директория кэша для моделей
DONUT_CACHE_DIR=./models

# Device (cpu или cuda)
DONUT_DEVICE=cpu

# Параметры генерации
DONUT_MAX_LENGTH=384
DONUT_NUM_BEAMS=1
DONUT_TEMPERATURE=1.0
```

### Типы документов и task prompts

В конфигурации определены следующие task prompts:

```python
{
    "waybill": "<s_waybill>",      # Накладные
    "invoice": "<s_invoice>",      # Счета-фактуры
    "act": "<s_act>",              # Акты выполненных работ
    "upd": "<s_upd>",              # Универсальные передаточные документы
}
```

---

## Особенности и рекомендации

### ✅ Преимущества Donut

- **End-to-end**: работает с документом целиком, без промежуточных этапов
- **Структурированный вывод**: возвращает JSON-like структуру
- **Многоязычный**: обучена на документах на разных языках
- **Быстро**: обработка одного документа ~2-3 сек на CPU

### ⚠️ Ограничения

- Требует `torch` и `transformers` (уже в requirements.txt)
- На CPU медленнее чем на GPU (рекомендуется ~3x ускорение на CUDA)
- Требует хорошей памяти (~2 ГБ на CPU)

### 🎯 Рекомендации

1. **Для production**: используйте GPU (`DONUT_DEVICE=cuda`)
2. **Для batch обработки**: рассмотрите использование Celery + Redis
3. **Для custom документов**: может потребоваться fine-tuning модели
4. **Обработка PDF**: сначала преобразуйте в изображение (используется внутри)

---

## Интеграция с основным OCR пайплайном

Если требуется комбинировать Donut с easyocr/paddleocr:

```python
# app/services/ocr_service.py
from app.ocr.donut_extractor import DonutExtractor

class OCRService:
    def __init__(self):
        # Основной OCR pipeline
        self._pipeline = OCRPipeline.from_settings()
        
        # Donut как дополнение
        if settings.DONUT_ENABLED:
            self._donut = DonutExtractor.from_pretrained(
                model_name_or_path=settings.DONUT_MODEL_NAME,
                device=settings.DONUT_DEVICE,
            )
    
    async def process_document(self, file_bytes, file_type, document_type, use_donut=False):
        if use_donut and self._donut:
            # Использовать Donut
            image = bytes_to_numpy(file_bytes, file_type)
            result = self._donut.extract(image, task_prompt=...)
        else:
            # Использовать стандартный pipeline
            result = await self._process_with_ocr(file_bytes, file_type, document_type)
        
        return result
```

---

## Trouble Shooting

### "Model not found"

```
Решение: Установите модель вручную или используйте дефолтное имя модели.
python -c "from transformers import DonutProcessor, VisionEncoderDecoderModel; \
           DonutProcessor.from_pretrained('naver-clova-ocr/donut-base'); \
           VisionEncoderDecoderModel.from_pretrained('naver-clova-ocr/donut-base')"
```

### "Out of memory"

```
Решение 1: Используйте CPU вместо GPU (медленнее, но надежнее)
Решение 2: Уменьшите MAX_IMAGE_DIMENSION в конфигурации
Решение 3: Добавьте swap на сервер
```

### "CUDA out of memory" (на GPU)

```
Решение: Используйте float16 вместо float32 в DonutExtractor
# Изменить в donut_extractor.py:
torch_dtype=torch.float16  # вместо torch.float32
```

---

## Лицензия и атрибуция

- **Donut**: [naver-clova-ocr/donut-base](https://huggingface.co/naver-clova-ocr/donut-base) — Apache 2.0
- **Трансформеры**: Hugging Face Transformers — Apache 2.0
