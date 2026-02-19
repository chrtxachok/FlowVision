# Transport OCR System

Система оптического распознавания текста для транспортных документов.

## Архитектура

- **web-app**: Django веб-приложение для управления документами
- **ocr-service**: FastAPI микросервис для OCR обработки
- **message-broker**: RabbitMQ для асинхронных задач
- **monitoring**: Prometheus и Grafana для мониторинга

## Быстрый старт

```
bash
# Копирование переменных окружения
cp .env.example .env

# Запуск всех сервисов
docker-compose -f infrastructure/docker-compose.yml up -d

# Запуск с GPU
docker-compose -f infrastructure/docker-compose.gpu.yml up -d
```

## Структура проекта

```
transport_ocr_system/
├── services/
│   ├── web-app/          # Django приложение
│   ├── ocr-service/      # FastAPI OCR сервис
│   ├── message-broker/   # RabbitMQ
│   └── monitoring/       # Мониторинг
├── infrastructure/       # Docker и конфигурация
├── shared/              # Общие компоненты
└── scripts/             # Скрипты деплоя
```

## Требования

- Docker и Docker Compose
- GPU (опционально для ML)
- MinIO для объектного хранения
