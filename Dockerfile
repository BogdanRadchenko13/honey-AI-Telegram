FROM python:3.11-slim

WORKDIR /app

# Копируем проект
COPY . /app/

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Делаем стартовый скрипт исполняемым
RUN chmod +x start.sh

# Запуск
CMD ["./start.sh"]
