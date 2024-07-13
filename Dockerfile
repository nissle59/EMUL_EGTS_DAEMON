# Базовый образ Python 3.10
FROM python:3.12-slim

# Обновляем пакеты и устанавливаем необходимые зависимости
#RUN apt-get update && \
#    apt-get install -y --no-install-recommends \
#    wireguard \
#    iproute2 \
#    iptables \
#    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /var/www/html

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все файлы в рабочую директорию
# COPY . .

# Открываем порт для WireGuard
# EXPOSE 51820/udp

# Инициализация базы данных
# RUN python init_db.py

# Команда для запуска эмулятора и вашего Python приложения
CMD ["/bin/bash", "-c", "python Emulator.py"]