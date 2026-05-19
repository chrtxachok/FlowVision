# Быстрый старт Donut API (PowerShell)
# Использование: .\scripts\donut_quickstart.ps1

Write-Host "🍩 FlowVision Donut API - Быстрый Старт (Windows)" -ForegroundColor Green
Write-Host "=" * 50

Write-Host ""

# 1. Проверка Python
Write-Host "1️⃣  Проверка Python..." -ForegroundColor Cyan
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Python не найден. Установите Python 3.11+" -ForegroundColor Red
    exit 1
}
Write-Host "✅ $pythonVersion" -ForegroundColor Green
Write-Host ""

# 2. Установка зависимостей
Write-Host "2️⃣  Установка зависимостей..." -ForegroundColor Cyan
pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Ошибка при установке зависимостей" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Зависимости установлены" -ForegroundColor Green
Write-Host ""

# 3. Создание .env файла
Write-Host "3️⃣  Проверка конфигурации (.env)..." -ForegroundColor Cyan
if (-not (Test-Path ".env")) {
    Write-Host "📝 Создание .env файла..." -ForegroundColor Yellow
    @"
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
"@ | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "✅ .env создан с default параметрами" -ForegroundColor Green
} else {
    Write-Host "✅ .env файл существует" -ForegroundColor Green
}
Write-Host ""

# 4. Проверка конфигурации
Write-Host "4️⃣  Проверка конфигурации Python..." -ForegroundColor Cyan
python -c @"
from app.config import settings
print(f'✅ DONUT_ENABLED: {settings.DONUT_ENABLED}')
print(f'✅ DONUT_MODEL_NAME: {settings.DONUT_MODEL_NAME}')
print(f'✅ DONUT_DEVICE: {settings.DONUT_DEVICE}')
print(f'✅ LOG_LEVEL: {settings.LOG_LEVEL}')
"@ | Write-Host -ForegroundColor Green

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Ошибка при проверке конфигурации" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 5. Предложение следующих шагов
Write-Host "5️⃣  Выбор режима работы:" -ForegroundColor Cyan
Write-Host ""
Write-Host "Вариант A: Локальное тестирование (без API сервера)" -ForegroundColor Yellow
Write-Host "  python scripts\test_donut_api.py --path static/image.jpg --doc-type invoice" -ForegroundColor White
Write-Host ""
Write-Host "Вариант B: Запуск API сервера" -ForegroundColor Yellow
Write-Host "  uvicorn app.main:app --reload" -ForegroundColor White
Write-Host ""
Write-Host "Вариант C: HTTP тестирование (требует запущенного сервера)" -ForegroundColor Yellow
Write-Host "  python scripts\test_donut_http.py --path static/image.jpg --doc-type invoice" -ForegroundColor White
Write-Host ""
Write-Host "=" * 50
Write-Host "✅ Все готово! Выберите вариант выше." -ForegroundColor Green
