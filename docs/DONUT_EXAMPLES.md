# Примеры результатов Donut API

## Пример 1: Invoice (Счет-фактура)

### Request

```bash
curl -X POST "http://localhost:8000/api/v1/donut/extract?document_type=invoice" \
  -F "file=@invoice.jpg"
```

### Response

```json
{
  "status": "success",
  "document_type": "invoice",
  "confidence": 0.96,
  "processing_time_ms": 2456,
  "extracted_data": {
    "invoice_number": {
      "value": "СФ-2024-05-001",
      "confidence": 0.98,
      "raw_text": "СФ-2024-05-001"
    },
    "date": {
      "value": "14.05.2024",
      "confidence": 0.97,
      "raw_text": "14.05.2024"
    },
    "seller": {
      "value": "ООО \"Логистик\"",
      "confidence": 0.95,
      "raw_text": "ООО \"Логистик\""
    },
    "buyer": {
      "value": "ПАО \"Транспортная компания\"",
      "confidence": 0.94,
      "raw_text": "ПАО \"Транспортная компания\""
    },
    "items": {
      "value": "[{\"name\": \"Услуга доставки\", \"quantity\": 1, \"price\": 15000}, ...]",
      "confidence": 0.92,
      "raw_text": "[{\"name\": \"Услуга доставки\", ...}]"
    },
    "total": {
      "value": "15000.00",
      "confidence": 0.97,
      "raw_text": "15000.00"
    },
    "currency": {
      "value": "RUB",
      "confidence": 0.99,
      "raw_text": "RUB"
    }
  },
  "raw_text": "<s_invoice>{\"invoice_number\": \"СФ-2024-05-001\", ...}</s_invoice>",
  "metadata": {
    "model": "naver-clova-ocr/donut-base",
    "model_type": "donut",
    "file_name": "invoice.jpg",
    "fields_found": 7
  }
}
```

---

## Пример 2: Waybill (Накладная / ТТН)

### Request

```bash
curl -X POST "http://localhost:8000/api/v1/donut/extract?document_type=waybill" \
  -F "file=@waybill.jpg"
```

### Response

```json
{
  "status": "success",
  "document_type": "waybill",
  "confidence": 0.94,
  "processing_time_ms": 2189,
  "extracted_data": {
    "waybill_number": {
      "value": "ТТН/1-20/000001",
      "confidence": 0.96,
      "raw_text": "ТТН/1-20/000001"
    },
    "date": {
      "value": "14.05.2024",
      "confidence": 0.98,
      "raw_text": "14.05.2024"
    },
    "sender": {
      "value": "ООО \"Логистик\", г. Москва, ул. Рабочая, д. 15",
      "confidence": 0.93,
      "raw_text": "ООО \"Логистик\", г. Москва, ул. Рабочая, д. 15"
    },
    "recipient": {
      "value": "ПАО \"Компания Б\", г. СПб, Невский пр., д. 120",
      "confidence": 0.91,
      "raw_text": "ПАО \"Компания Б\", г. СПб, Невский пр., д. 120"
    },
    "cargo_description": {
      "value": "Мебель для офиса, коробки 5 шт",
      "confidence": 0.90,
      "raw_text": "Мебель для офиса, коробки 5 шт"
    },
    "cargo_mass_kg": {
      "value": "150",
      "confidence": 0.95,
      "raw_text": "150 кг"
    },
    "cargo_volume_m3": {
      "value": "2.5",
      "confidence": 0.92,
      "raw_text": "2.5 м³"
    },
    "total_amount": {
      "value": "5000.00",
      "confidence": 0.96,
      "raw_text": "5000.00 руб"
    },
    "driver_name": {
      "value": "Иван Петров",
      "confidence": 0.88,
      "raw_text": "Иван Петров"
    },
    "driver_license": {
      "value": "77ВХ123456",
      "confidence": 0.87,
      "raw_text": "77ВХ123456"
    },
    "vehicle_number": {
      "value": "А123БВ77",
      "confidence": 0.97,
      "raw_text": "А123БВ77"
    },
    "vehicle_vin": {
      "value": "X96CK5A58A0001234",
      "confidence": 0.85,
      "raw_text": "X96CK5A58A0001234"
    },
    "loading_location": {
      "value": "Москва, склад №1",
      "confidence": 0.92,
      "raw_text": "Москва, склад №1"
    },
    "unloading_location": {
      "value": "СПб, офис компании",
      "confidence": 0.91,
      "raw_text": "СПб, офис компании"
    }
  },
  "raw_text": "<s_waybill>{\"waybill_number\": \"ТТН/1-20/000001\", ...}</s_waybill>",
  "metadata": {
    "model": "naver-clova-ocr/donut-base",
    "model_type": "donut",
    "file_name": "waybill.jpg",
    "fields_found": 13
  }
}
```

---

## Пример 3: Act (Акт выполненных работ)

### Request

```bash
curl -X POST "http://localhost:8000/api/v1/donut/extract?document_type=act" \
  -F "file=@act.jpg"
```

### Response

```json
{
  "status": "success",
  "document_type": "act",
  "confidence": 0.93,
  "processing_time_ms": 2301,
  "extracted_data": {
    "act_number": {
      "value": "АКТ-2024-05-001",
      "confidence": 0.97,
      "raw_text": "АКТ-2024-05-001"
    },
    "date": {
      "value": "14.05.2024",
      "confidence": 0.98,
      "raw_text": "14.05.2024"
    },
    "period_from": {
      "value": "01.05.2024",
      "confidence": 0.96,
      "raw_text": "01.05.2024"
    },
    "period_to": {
      "value": "31.05.2024",
      "confidence": 0.96,
      "raw_text": "31.05.2024"
    },
    "contractor": {
      "value": "ООО \"Сервис Плюс\"",
      "confidence": 0.94,
      "raw_text": "ООО \"Сервис Плюс\""
    },
    "customer": {
      "value": "ПАО \"Логистика\"",
      "confidence": 0.95,
      "raw_text": "ПАО \"Логистика\""
    },
    "work_description": {
      "value": "Ремонт и обслуживание логистического оборудования",
      "confidence": 0.91,
      "raw_text": "Ремонт и обслуживание логистического оборудования"
    },
    "work_items": {
      "value": "[{\"description\": \"Замена ремня\", \"hours\": 2, \"rate\": 500}, ...]",
      "confidence": 0.89,
      "raw_text": "[...]"
    },
    "total_hours": {
      "value": "40",
      "confidence": 0.97,
      "raw_text": "40 часов"
    },
    "total_amount": {
      "value": "20000.00",
      "confidence": 0.96,
      "raw_text": "20000.00 руб"
    },
    "signed_by_contractor": {
      "value": "А.И. Петров",
      "confidence": 0.85,
      "raw_text": "А.И. Петров"
    },
    "signed_by_customer": {
      "value": "И.П. Сидоров",
      "confidence": 0.84,
      "raw_text": "И.П. Сидоров"
    }
  },
  "raw_text": "<s_act>{\"act_number\": \"АКТ-2024-05-001\", ...}</s_act>",
  "metadata": {
    "model": "naver-clova-ocr/donut-base",
    "model_type": "donut",
    "file_name": "act.jpg",
    "fields_found": 11
  }
}
```

---

## Пример 4: UPD (Универсальный передаточный документ)

### Request

```bash
curl -X POST "http://localhost:8000/api/v1/donut/extract?document_type=upd" \
  -F "file=@upd.jpg"
```

### Response

```json
{
  "status": "success",
  "document_type": "upd",
  "confidence": 0.95,
  "processing_time_ms": 2234,
  "extracted_data": {
    "upd_number": {
      "value": "УПД-2024-001/1",
      "confidence": 0.97,
      "raw_text": "УПД-2024-001/1"
    },
    "date": {
      "value": "14.05.2024",
      "confidence": 0.98,
      "raw_text": "14.05.2024"
    },
    "seller": {
      "value": "ООО \"Логистик\", ИНН 7700000001",
      "confidence": 0.96,
      "raw_text": "ООО \"Логистик\", ИНН 7700000001"
    },
    "buyer": {
      "value": "ПАО \"Компания\", ИНН 7700000002",
      "confidence": 0.95,
      "raw_text": "ПАО \"Компания\", ИНН 7700000002"
    },
    "table_items": {
      "value": "[{\"item_number\": 1, \"description\": \"Услуга доставки\", \"unit\": \"услуга\", \"quantity\": 1, \"price\": 10000, \"tax_rate\": \"18%\", \"tax_amount\": 1800, \"amount\": 11800}, ...]",
      "confidence": 0.93,
      "raw_text": "[...]"
    },
    "subtotal": {
      "value": "10000.00",
      "confidence": 0.97,
      "raw_text": "10000.00"
    },
    "tax": {
      "value": "1800.00",
      "confidence": 0.97,
      "raw_text": "1800.00"
    },
    "total_with_tax": {
      "value": "11800.00",
      "confidence": 0.97,
      "raw_text": "11800.00"
    },
    "payment_method": {
      "value": "Счет",
      "confidence": 0.96,
      "raw_text": "Счет"
    },
    "bank_details": {
      "value": "БИК 044525225, Счёт 40702810123456789012",
      "confidence": 0.91,
      "raw_text": "БИК 044525225, Счёт 40702810123456789012"
    }
  },
  "raw_text": "<s_upd>{\"upd_number\": \"УПД-2024-001/1\", ...}</s_upd>",
  "metadata": {
    "model": "naver-clova-ocr/donut-base",
    "model_type": "donut",
    "file_name": "upd.jpg",
    "fields_found": 11
  }
}
```

---

## Ошибки и их обработка

### Пример 1: Неподдерживаемый формат файла

```bash
curl -X POST "http://localhost:8000/api/v1/donut/extract?document_type=invoice" \
  -F "file=@document.txt"
```

**Response (400):**

```json
{
  "detail": "Unsupported file type: text/plain. Supported: image/jpeg, image/png, application/pdf"
}
```

### Пример 2: Файл слишком большой

```bash
curl -X POST "http://localhost:8000/api/v1/donut/extract?document_type=invoice" \
  -F "file=@huge_document.jpg"
```

**Response (413):**

```json
{
  "detail": "File too large: 52428800 bytes (max: 10485760)"
}
```

### Пример 3: Модель не загружена

```bash
curl -X POST "http://localhost:8000/api/v1/donut/extract?document_type=invoice" \
  -F "file=@document.jpg"
```

**Response (500):**

```json
{
  "detail": "Failed to initialize Donut model: [torch.cuda.OutOfMemoryError] CUDA out of memory..."
}
```

---

## Парсинг JSON результата

### Request

```bash
curl -X POST "http://localhost:8000/api/v1/donut/parse-json" \
  -G \
  --data-urlencode 'raw_output={"invoice_number":"INV001","date":"2024-05-14","total":5000}' \
  --data-urlencode 'document_type=invoice'
```

### Response

```json
{
  "success": true,
  "document_type": "invoice",
  "extracted_data": {
    "invoice_number": "INV001",
    "date": "2024-05-14",
    "total": 5000
  }
}
```

---

## Информация о модели

### Request

```bash
curl -X GET "http://localhost:8000/api/v1/donut/info"
```

### Response

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

---

## Интеграция результатов

### Python

```python
import requests
import json

response = requests.post(
    "http://localhost:8000/api/v1/donut/extract?document_type=invoice",
    files={'file': open('invoice.jpg', 'rb')}
)

data = response.json()

# Извлечение конкретных полей
invoice_number = data['extracted_data']['invoice_number']['value']
total = float(data['extracted_data']['total']['amount']['value'])
confidence = data['confidence']

print(f"Invoice: {invoice_number}, Total: {total}, Confidence: {confidence:.0%}")
```

### JavaScript

```javascript
async function processDocument(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(
        'http://localhost:8000/api/v1/donut/extract?document_type=invoice',
        { method: 'POST', body: formData }
    );
    
    const data = await response.json();
    
    // Использование результатов
    console.log(data.extracted_data);
    console.log(`Processed in ${data.processing_time_ms}ms`);
    
    return data;
}
```

---

**Примеры обновлены**: 2024-05-14
