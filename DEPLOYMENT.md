# Инструкция по развертыванию Meow Bot на сервере

## Требования к серверу

- Ubuntu 18.04+ или Debian 9+
- Python 3.8+
- Доступ к интернету
- Права суперпользователя (sudo)

## Шаг 1: Подготовка сервера

### 1.1 Обновление системы
```bash
sudo apt update && sudo apt upgrade -y
```

### 1.2 Установка Python и pip
```bash
sudo apt install python3 python3-pip python3-venv -y
```

### 1.3 Установка Git (если нужно)
```bash
sudo apt install git -y
```

## Шаг 2: Загрузка проекта

### 2.1 Клонирование репозитория
```bash
git clone <ваш-репозиторий> my-meow-bot
cd my-meow-bot
```

### 2.2 Или загрузка файлов вручную
Если у вас нет Git репозитория, просто скопируйте все файлы проекта в папку на сервере.

## Шаг 3: Настройка Python окружения

### 3.1 Создание виртуального окружения
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3.2 Установка зависимостей
```bash
pip install -r requirements.txt
```

## Шаг 4: Настройка токена бота

### 4.1 Получение токена
1. Откройте Telegram
2. Найдите @BotFather
3. Отправьте команду `/newbot` (или используйте существующий бот)
4. Следуйте инструкциям и получите токен

### 4.2 Создание файла .env
```bash
nano .env
```

Добавьте в файл:
```
BOT_TOKEN=ваш_реальный_токен_бота
```

Сохраните файл (Ctrl+X, затем Y, затем Enter).

## Шаг 5: Тестирование бота

### 5.1 Запуск в тестовом режиме
```bash
source venv/bin/activate
python bot.py
```

Если все работает правильно, вы увидите сообщение "Бот успешно запущен и готов к работе!"

Остановите бота (Ctrl+C).

## Шаг 6: Установка как systemd сервис

### 6.1 Установка сервиса
```bash
sudo ./manage_bot.sh install
```

### 6.2 Запуск бота
```bash
sudo ./manage_bot.sh start
```

### 6.3 Проверка статуса
```bash
sudo ./manage_bot.sh status
```

## Шаг 7: Управление ботом

### Основные команды управления:

```bash
# Запуск бота
sudo ./manage_bot.sh start

# Остановка бота
sudo ./manage_bot.sh stop

# Перезапуск бота
sudo ./manage_bot.sh restart

# Просмотр статуса
sudo ./manage_bot.sh status

# Просмотр логов systemd
sudo ./manage_bot.sh logs

# Просмотр логов из файлов
sudo ./manage_bot.sh file-logs
```

### Прямые команды systemctl:
```bash
# Запуск
sudo systemctl start meow-bot

# Остановка
sudo systemctl stop meow-bot

# Перезапуск
sudo systemctl restart meow-bot

# Статус
sudo systemctl status meow-bot

# Включение автозапуска
sudo systemctl enable meow-bot

# Отключение автозапуска
sudo systemctl disable meow-bot
```

## Шаг 8: Мониторинг и логи

### 8.1 Просмотр логов в реальном времени
```bash
sudo journalctl -u meow-bot -f
```

### 8.2 Просмотр логов за определенный период
```bash
# За последний час
sudo journalctl -u meow-bot --since "1 hour ago"

# За сегодня
sudo journalctl -u meow-bot --since "today"

# За последние 100 строк
sudo journalctl -u meow-bot -n 100
```

### 8.3 Логи в файлах
Логи также сохраняются в папке `logs/` в формате `bot_YYYYMMDD.log`

## Шаг 9: Обновление бота

### 9.1 Остановка бота
```bash
sudo ./manage_bot.sh stop
```

### 9.2 Обновление кода
```bash
git pull  # если используете Git
# или замените файлы вручную
```

### 9.3 Обновление зависимостей (если нужно)
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 9.4 Запуск обновленного бота
```bash
sudo ./manage_bot.sh start
```

## Шаг 10: Безопасность

### 10.1 Настройка файрвола (опционально)
```bash
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
```

### 10.2 Регулярное обновление системы
```bash
sudo apt update && sudo apt upgrade -y
```

## Устранение неполадок

### Проблема: Бот не запускается
1. Проверьте токен в файле `.env`
2. Проверьте логи: `sudo ./manage_bot.sh logs`
3. Убедитесь, что все зависимости установлены

### Проблема: Бот не отвечает
1. Проверьте интернет-соединение
2. Проверьте статус: `sudo ./manage_bot.sh status`
3. Проверьте логи на ошибки

### Проблема: Ошибки с правами доступа
1. Убедитесь, что запускаете команды с sudo
2. Проверьте права на папку проекта

### Проблема: Бот падает
1. Проверьте логи: `sudo journalctl -u meow-bot -n 50`
2. Убедитесь, что Python и зависимости установлены правильно

## Полезные команды

```bash
# Перезагрузка systemd
sudo systemctl daemon-reload

# Проверка конфигурации сервиса
sudo systemctl cat meow-bot

# Просмотр всех логов
sudo journalctl -u meow-bot --no-pager

# Очистка старых логов
sudo journalctl --vacuum-time=7d
```

## Контакты для поддержки

Если у вас возникли проблемы, проверьте:
1. Логи бота
2. Статус сервиса
3. Настройки сети
4. Правильность токена

Удачного развертывания! 🐱 