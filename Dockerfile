FROM python:3.11-slim AS builder

# Установка зависимостей системы
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgl1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libglib2.0-0 \
    libfontconfig1 \
    poppler-utils \
    ca-certificates \
    tesseract-ocr \
    tesseract-ocr-rus \
    && rm -rf /var/lib/apt/lists/*

# Установка переменных окружения
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Создание рабочей директории
WORKDIR /app

# Копирование зависимостей
# Зеркало: -i https://pypi.tuna.tsinghua.edu.cn/simple \
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Копирование кода
COPY app ./app
# COPY models ./models
COPY scripts ./scripts

RUN mkdir -p /app/models

# Создание пользователя без прав root
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Экспозиция порта
EXPOSE 8080

# Запуск приложения
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]

