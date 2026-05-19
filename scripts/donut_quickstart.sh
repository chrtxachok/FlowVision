#!/bin/bash
# Быстрый старт Donut API

echo "🍩 FlowVision Donut API - Быстрый Старт"
echo "=========================================="
echo ""

# 1. Проверка Python
echo "1️⃣  Проверка Python..."
python --version
if [ $? -ne 0 ]; then
    echo "❌ Python не найден. Установите Python 3.11+"
    exit 1
fi
echo "✅ Python найден"
echo ""

# 2. Установка зависимостей
echo "2️⃣  Установка зависимостей..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "❌ Ошибка при установке зависимостей"
    exit 1
fi
echo "✅ Зависимости установлены"
echo ""

# 3. Создание .env файла
echo "3️⃣  Проверка конфигурации (.env)..."
if [ ! -f ".env" ]; then
    echo "📝 Создание .env файла..."
    cat > .env << EOF
# Donut Configuration
DONUT_ENABLED=true
DONUT_MODEL_NAME=naver-clova-ocr/donut-base
DONUT_DEVICE=cpu
DONUT_MAX_LENGTH=384
DONUT_NUM_BEAMS=1
DONUT_TEMPERATURE=1.0

# Other settings
API_KEY=dev-secret-key-change-in-production
DEBUG=false
LOG_LEVEL=INFO
MAX_FILE_SIZE=10485760
EOF
    echo "✅ .env создан с default параметрами"
else
    echo "✅ .env файл существует"
fi
echo ""

# 4. Проверка конфигурации
echo "4️⃣  Проверка конфигурации Python..."
python -c "
from app.config import settings
print(f'✅ DONUT_ENABLED: {settings.DONUT_ENABLED}')
print(f'✅ DONUT_MODEL_NAME: {settings.DONUT_MODEL_NAME}')
print(f'✅ DONUT_DEVICE: {settings.DONUT_DEVICE}')
print(f'✅ LOG_LEVEL: {settings.LOG_LEVEL}')
" || exit 1
echo ""

# 5. Предложение следующих шагов
echo "5️⃣  Выбор режима работы:"
echo ""
echo "Вариант A: Локальное тестирование (без API сервера)"
echo "  python scripts/test_donut_api.py --path static/image.jpg --doc-type invoice"
echo ""
echo "Вариант B: Запуск API сервера"
echo "  uvicorn app.main:app --reload"
echo ""
echo "Вариант C: HTTP тестирование (требует запущенного сервера)"
echo "  python scripts/test_donut_http.py --path static/image.jpg --doc-type invoice"
echo ""
echo "=========================================="
echo "✅ Все готово! Выберите вариант выше."
