FROM ghcr.io/tesseract-ocr/tesseract:5.4.0

ENV DEBIAN_FRONTEND=noninteractive

# Ставим Python + нужные либы
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip ffmpeg libglib2.0-0 libsm6 libxext6 libxrender1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY honey-AI-Telegram-main/ /app/

RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir pytesseract easyocr

RUN chmod +x start.sh

CMD ["./start.sh"]
