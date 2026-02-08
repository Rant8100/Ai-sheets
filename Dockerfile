# 1. Используем легкий Python
FROM python:3.11-slim

# 2. Отключаем буферизацию (чтобы логи виделись сразу)
ENV PYTHONUNBUFFERED=1

# 3. Устанавливаем рабочую папку
WORKDIR /app

# 4. Устанавливаем системные библиотеки (нужны для аудио/ffmpeg)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# 5. Копируем файл зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Копируем весь код бота
COPY . .

# 7. Запускаем бота
CMD ["python", "main.py"]