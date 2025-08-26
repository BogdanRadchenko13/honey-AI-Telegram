FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# Минимальные зависимости для OCR + OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копируем проект
COPY honey-AI-Telegram-main/ /app/

# Устанавливаем Python-зависимости
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir easyocr

# Делаем стартовый скрипт исполняемым
RUN chmod +x start.sh

# Запуск
CMD ["./start.sh"]
