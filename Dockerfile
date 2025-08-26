FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libglib2.0-0 libsm6 libxext6 libxrender1 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY honey-AI-Telegram-main/ /app/

RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir pytesseract easyocr

RUN chmod +x start.sh

CMD ["./start.sh"]
