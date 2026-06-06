FROM python:3.11-slim

LABEL maintainer="FlowVision Team"

# Системные зависимости ТОЛЬКО для OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libglib2.0-0 \
    curl \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Переменные окружения
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Копирование кода
COPY ./app ./app
COPY ./static ./static
COPY ./scripts ./scripts
COPY ./logika.py ./logika.py
COPY ./project-1-at-2026-04-18-05-40-eb2e8e7a.json ./project-1-at-2026-04-18-05-40-eb2e8e7a.json
# Предобученные модели для logika.WaybillExtractor (как в test_gui.py)
COPY ./field_classifier.pkl ./field_classifier.pkl
COPY ./scaler.pkl ./scaler.pkl
COPY ./field_coords.pkl ./field_coords.pkl




# Создание директорий
RUN mkdir -p /app/models /app/logs /app/data /app/cache

# Копирование скрипта запуска
COPY ./scripts/entrypoint.sh /entrypoint.sh
RUN dos2unix /entrypoint.sh 
RUN chmod +x /entrypoint.sh

# Создание пользователя
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]