#!/bin/bash
# Скрипт для запуска бота с новой модульной структурой

cd "$(dirname "$0")"

# Активируем виртуальное окружение
source venv/bin/activate

# Запускаем бота
python bot.py
