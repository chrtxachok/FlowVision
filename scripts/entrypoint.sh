#!/bin/bash
set -e

echo "🚀 Запуск FlowVision OCR..."

# Проверка наличия модели
if [ ! -d "${LOCAL_MODEL_PATH:-/app/models/donut-trained}" ]; then
    echo "⚠️  Model directory not found: ${LOCAL_MODEL_PATH:-/app/models/donut-trained}"
    echo "💡 Hint: Mount model via -v or download it first"
fi

# Создание необходимых директорий
mkdir -p /app/logs /app/data/exports

# Установка прав
chmod -R 755 /app/logs /app/data 2>/dev/null || true

echo "✅ Инициализация завершена"
echo "📡 API доступен на http://${API_HOST:-0.0.0.0}:${API_PORT:-8000}"
echo "🔍 Health check: http://localhost:${API_PORT:-8000}/health"

# Запуск основного приложения
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
