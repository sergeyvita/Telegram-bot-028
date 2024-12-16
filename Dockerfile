# Использование легковесного Python-образа
FROM python:3.11-slim

# Установка Tesseract OCR и необходимых библиотек
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Установка зависимостей Python
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование файлов проекта
COPY . .

# Установка переменных окружения
ENV TESSERACT_CMD=/usr/bin/tesseract

# Запуск приложения
CMD ["python", "main.py"]
