FROM python:3.10-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libpq-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Установка PaddlePaddle CPU версии
RUN pip install paddlepaddle==2.6.0 -i https://mirror.baidu.com/pypi/simple

# Рабочая директория
WORKDIR /app

# Копирование зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY src/ ./src/
COPY config.yaml .
COPY models/ ./models/

# Создание директории для моделей
RUN mkdir -p /app/models/layoutlm /app/models/dbnet

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV PADDLEOCR_ROOT=/app/models

# Запуск сервиса
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
