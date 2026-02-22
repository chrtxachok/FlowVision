FROM python:3.11-slim

# Установка зависимостей системы
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-rus \
    && rm -rf /var/lib/apt/lists/*

# Установка переменных окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Создание рабочей директории
WORKDIR /app

# Копирование зависимостей
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY app ./app
COPY models ./models
COPY scripts ./scripts

# Создание пользователя без прав root
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Экспозиция порта
EXPOSE 8080

# Запуск приложения
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]