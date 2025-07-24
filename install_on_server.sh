#!/bin/bash

# Скрипт для установки Meow Bot на удаленном сервере
echo "Установка Meow Bot сервиса..."

# Останавливаем сервис если он запущен
sudo systemctl stop meow-bot 2>/dev/null

# Копируем файл сервиса
sudo cp meow-bot.service /etc/systemd/system/

# Перезагружаем systemd
sudo systemctl daemon-reload

# Включаем автозапуск
sudo systemctl enable meow-bot

# Запускаем сервис
sudo systemctl start meow-bot

# Проверяем статус
echo "Статус сервиса:"
sudo systemctl status meow-bot --no-pager

echo ""
echo "Для просмотра логов используйте:"
echo "sudo journalctl -u meow-bot -f"
echo ""
echo "Для управления сервисом используйте:"
echo "sudo systemctl start/stop/restart meow-bot" 