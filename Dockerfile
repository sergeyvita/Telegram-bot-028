# Базовый образ Python
FROM python:3.11-slim

# Установка системных зависимостей для Tesseract
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && apt-get clean

# Установка рабочей директории
WORKDIR /app

# Копирование всех файлов проекта в контейнер
COPY . .

# Установка зависимостей Python
RUN pip install --no-cache-dir -r requirements.txt

# Установка порта и запуск приложения
CMD ["python", "main.py"]
