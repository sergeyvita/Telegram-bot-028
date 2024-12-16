# Использование легковесного Python-образа
FROM python:3.11-slim

# Установка зависимостей Python
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование файлов проекта
COPY . .

# Запуск приложения
CMD ["python", "main.py"]
