# 📚 Donut API Documentation Index

Полная документация API Donut интеграции в FlowVision OCR сервис.

## 🗺️ Навигация по документам

### Для новичков

1. **[DONUT_README.md](./DONUT_README.md)** ⭐
   - Обзор проекта и архитектуры
   - Быстрый старт за 5 минут
   - Основные компоненты

2. **[DONUT_SETUP.md](./DONUT_SETUP.md)**
   - Подробная инструкция по установке
   - Конфигурация переменных окружения
   - Troubleshooting для типичных проблем

### Для разработчиков

3. **[DONUT_API.md](./DONUT_API.md)** 📖
   - Полная REST API документация
   - Описание всех endpoints
   - Примеры запросов (curl, Python, JavaScript)
   - Коды ошибок и их обработка

4. **[DONUT_EXAMPLES.md](./DONUT_EXAMPLES.md)** 💡
   - Примеры результатов для каждого типа документа
   - Invoice, Waybill, Act, UPD
   - Обработка ошибок
   - Интеграция с вашим кодом

### Для тестирования

5. **[Postman_Donut_API.json](./Postman_Donut_API.json)**
   - Готовая коллекция Postman для тестирования
   - Pre-built запросы со всеми endpoints
   - Автоматические тесты

### Локальные скрипты

- **[scripts/test_donut_api.py](../scripts/test_donut_api.py)**
  - Локальное тестирование модели (без HTTP)
  - Отладка работы Donut

- **[scripts/test_donut_http.py](../scripts/test_donut_http.py)**
  - Тестирование HTTP API
  - Проверка доступности сервера

---

## 🎯 Быстрая справка

### Установка и запуск

```bash
# 1. Установите зависимости
pip install -r requirements.txt

# 2. Настройте .env
export DONUT_ENABLED=true
export DONUT_DEVICE=cpu  # или cuda

# 3. Запустите сервер
uvicorn app.main:app --reload

# 4. Тестируйте API
curl -X POST "http://localhost:8000/api/v1/donut/extract?document_type=invoice" \
  -F "file=@document.jpg"
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Проверка здоровья |
| POST | `/api/v1/donut/extract` | Извлечение данных из документа |
| GET | `/api/v1/donut/info` | Информация о модели |
| POST | `/api/v1/donut/parse-json` | Парсинг JSON результата |

### Типы документов

```
document_type=invoice  # Счета-фактуры
document_type=waybill  # Накладные (ТТН)
document_type=act      # Акты выполненных работ
document_type=upd      # Универсальные передаточные документы
```

---

## 📁 Структура проекта

```
FlowVision/
├── app/
│   ├── ocr/
│   │   └── donut_extractor.py          # ⭐ Core Donut класс
│   ├── api/
│   │   └── donut_routes.py             # ⭐ REST endpoints
│   ├── processors/
│   │   └── donut.py                    # Document processor
│   └── config.py                       # Конфигурация (Donut параметры)
│
├── scripts/
│   ├── test_donut_api.py               # Локальное тестирование
│   └── test_donut_http.py              # HTTP тестирование
│
├── docs/
│   ├── DONUT_README.md                 # Этот файл
│   ├── DONUT_API.md                    # API документация
│   ├── DONUT_SETUP.md                  # Инструкции по настройке
│   ├── DONUT_EXAMPLES.md               # Примеры результатов
│   ├── Postman_Donut_API.json          # Postman коллекция
│   └── INDEX.md                        # Этот файл
│
└── requirements.txt                    # Зависимости (включая transformers)
```

---

## 🚀 Typical Workflows

### Workflow 1: Локальное тестирование

```bash
# Сценарий: проверить работу модели на вашей машине
python scripts/test_donut_api.py --path static/image.jpg --doc-type waybill
```

**Результат**: Видите результат extraction прямо в консоли, без HTTP сервера.

### Workflow 2: Запуск API сервера

```bash
# Сценарий: развернуть API для использования другими приложениями
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Результат**: API доступен на `http://localhost:8000`, можно тестировать через Postman или curl.

### Workflow 3: HTTP тестирование

```bash
# Сценарий: протестировать API через HTTP
python scripts/test_donut_http.py --path document.jpg --doc-type invoice
```

**Результат**: Отправляет документ на запущенный API сервер, получает результат.

### Workflow 4: Docker deployment

```bash
# Сценарий: развернуть в production
docker-compose up -d
```

**Результат**: API запущена в контейнере, готова к использованию.

---

## ✅ Checklist для использования

- [ ] Установлены зависимости (`pip install -r requirements.txt`)
- [ ] Python 3.11-3.13 установлен
- [ ] `.env` файл создан и сконфигурирован
- [ ] Проверена конфигурация: `python -c "from app.config import settings; print(settings.DONUT_ENABLED)"`
- [ ] Протестирована локально: `python scripts/test_donut_api.py --path static/image.jpg`
- [ ] Запущен сервер: `uvicorn app.main:app --reload`
- [ ] Проверена доступность: `curl http://localhost:8000/health`
- [ ] Получена информация о модели: `curl http://localhost:8000/api/v1/donut/info`
- [ ] Отправлен тестовый документ: `curl -X POST ... -F "file=@document.jpg"`

---

## 🐛 Частые вопросы

### Q: Нужен ли GPU для использования Donut?
**A**: Нет, работает на CPU, но на GPU будет в 3-4 раза быстрее.

### Q: Какой размер модели?
**A**: donut-base ~230 МБ, потребляет ~1-2 ГБ памяти.

### Q: Что делать если модель не загружается?
**A**: Смотрите раздел [Troubleshooting](./DONUT_SETUP.md#-trouble-shooting) в DONUT_SETUP.md.

### Q: Как интегрировать с моей системой?
**A**: Смотрите примеры в [DONUT_EXAMPLES.md](./DONUT_EXAMPLES.md).

### Q: Поддерживаются ли custom документы?
**A**: Да, потребуется fine-tuning модели. Смотрите документацию Donut.

---

## 📊 Стек технологий

- **Transformers**: 4.30.0+ (HuggingFace)
- **PyTorch**: 2.0+
- **FastAPI**: 0.100+
- **Python**: 3.11-3.13

---

## 🎓 Обучение

### Минимум необходимо знать:

1. **REST API** — GET/POST запросы
2. **JSON** — формат данных
3. **Python** — для локального тестирования (опционально)

### Дополнительно:

- Docker для deployment
- CUDA/GPU optimization
- Fine-tuning моделей (для custom документов)

---

## 📞 Получить помощь

1. **Документация**: Прочитайте соответствующий файл из списка выше
2. **Примеры**: Смотрите [DONUT_EXAMPLES.md](./DONUT_EXAMPLES.md)
3. **Тестирование**: Используйте `test_donut_api.py` или `test_donut_http.py`
4. **Логирование**: Включите DEBUG уровень в конфигурации

---

## 📝 Версия документации

- **Версия**: 1.0.0
- **Последнее обновление**: 14 мая 2024
- **Статус**: Production Ready ✅

---

## 🔗 Полезные ссылки

- [Donut GitHub](https://github.com/clovaai/donut)
- [Donut Paper](https://arxiv.org/abs/2111.15664)
- [HuggingFace Model Card](https://huggingface.co/naver-clova-ocr/donut-base)
- [Transformers Docs](https://huggingface.co/docs/transformers/)
- [FlowVision README](../readme.md)

---

**Последнее изменение**: 2024-05-14  
**Автор**: AI Assistant  
**Лицензия**: Apache 2.0
