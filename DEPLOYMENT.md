# Инструкция по развертыванию Meow Bot на сервере

## Требования к серверу

- Ubuntu 18.04+ или Debian 9+
- Python 3.11+ (рекомендуется для лучшей совместимости)
- Доступ к интернету
- Права суперпользователя (sudo)
- Минимум 512 МБ RAM
- 1 ГБ свободного места на диске

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

# Настройки логирования (опционально)
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_TO_FILE=true                  # Логировать в файл (true/false)
LOG_TO_CONSOLE=true               # Логировать в консоль (true/false)
LOG_DIR=logs                      # Директория для логов
LOG_MAX_DAYS=7                    # Количество дней хранения логов
```

Сохраните файл (Ctrl+X, затем Y, затем Enter).

## Шаг 5: Структура проекта

### 5.1 Модульная архитектура
Проект имеет следующую структуру:

```
my-meow-bot/
├── bot.py                    # Точка входа
├── src/                      # Основной код
│   ├── main.py              # Главный модуль
│   ├── constants.py         # Константы и настройки
│   ├── config/
│   │   └── settings.py      # Конфигурация
│   ├── handlers/            # Обработчики команд
│   │   ├── basic_commands.py
│   │   ├── meetings.py
│   │   ├── edit_meetings.py
│   │   ├── settings.py
│   │   └── callbacks.py
│   └── utils/               # Утилиты
│       ├── helpers.py
│       ├── logging_manager.py
│       └── rate_limiter.py
├── database.py              # Работа с БД
├── reminder_system.py       # Система напоминаний
├── meetings.db              # База данных SQLite
├── logs/                    # Логи (создается автоматически)
├── requirements.txt         # Зависимости
├── .env                     # Переменные окружения
└── manage_bot.sh           # Скрипт управления
```

## Шаг 6: Тестирование бота

### 6.1 Запуск в тестовом режиме
```bash
source venv/bin/activate
python bot.py
```

Если все работает правильно, вы увидите сообщения:
```
- Система логирования инициализирована. Уровень: INFO
- Логи сохраняются в: logs/
- Бот успешно запущен и готов к работе!
- Система напоминаний запущена
```

Остановите бота (Ctrl+C).

## Шаг 7: Установка как systemd сервис

### 7.1 Установка сервиса
```bash
sudo ./manage_bot.sh install
```

### 7.2 Запуск бота
```bash
sudo ./manage_bot.sh start
```

### 7.3 Проверка статуса
```bash
sudo ./manage_bot.sh status
```

## Шаг 8: Управление ботом

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

## Шаг 9: Мониторинг и логи

### 9.1 Системные логи (systemd)
```bash
# Просмотр логов в реальном времени
sudo journalctl -u meow-bot -f

# За последний час
sudo journalctl -u meow-bot --since "1 hour ago"

# За сегодня
sudo journalctl -u meow-bot --since "today"

# За последние 100 строк
sudo journalctl -u meow-bot -n 100
```

### 9.2 Логи приложения (файлы)
Бот автоматически создает логи в папке `logs/` с ежедневной ротацией:

```bash
# Просмотр текущих логов
tail -f logs/bot_$(date +%Y%m%d).log

# Просмотр всех файлов логов
ls -la logs/

# Статистика использования места
du -sh logs/

# Просмотр последних 50 строк
tail -50 logs/bot_$(date +%Y%m%d).log

# Поиск ошибок в логах
grep -i "error\|exception\|critical" logs/bot_*.log
```

### 9.3 Автоматическая очистка логов
Бот автоматически удаляет старые логи согласно настройке `LOG_MAX_DAYS` в `.env` файле.

### 9.4 Мониторинг производительности
```bash
# Использование памяти и CPU ботом
ps aux | grep "python.*bot.py"

# Общая статистика системы
htop

# Место на диске
df -h

# Статус сетевых соединений
netstat -tulpn | grep python
```

## Шаг 10: Обновление бота

### 10.1 Остановка бота
```bash
sudo ./manage_bot.sh stop
```

### 10.2 Обновление кода
```bash
git pull  # если используете Git
# или замените файлы вручную
```

### 10.3 Обновление зависимостей (если нужно)
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### 10.4 Запуск обновленного бота
```bash
sudo ./manage_bot.sh start
```

## Шаг 11: Безопасность и оптимизация

### 11.1 Настройка файрвола (опционально)
```bash
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
```

### 11.2 Регулярное обновление системы
```bash
sudo apt update && sudo apt upgrade -y
```

### 11.3 Меры безопасности бота
Бот включает следующие встроенные меры безопасности:

- **Ограничения длины ввода:**
  - Названия встреч: максимум 200 символов
  - Описания: максимум 1000 символов

- **Rate Limiting:**
  - Максимум 50 встреч в день на пользователя
  - Автоматический сброс лимитов каждый день

- **Безопасное логирование:**
  - Персональные данные не сохраняются в логах
  - Логируются только ID пользователей и встреч

- **Защита базы данных:**
  - Параметризованные SQL-запросы
  - Изоляция данных пользователей

### 11.4 Рекомендации по безопасности
```bash
# Ограничение доступа к файлам
chmod 600 .env
chmod 755 *.py
chmod -R 755 src/

# Создание отдельного пользователя для бота (рекомендуется)
sudo useradd -r -s /bin/false meowbot
sudo chown -R meowbot:meowbot /path/to/my-meow-bot

# Регулярное резервное копирование базы данных
cp meetings.db meetings.db.backup.$(date +%Y%m%d)
```

## Устранение неполадок

### Проблема: Бот не запускается
1. **Проверьте токен в файле `.env`**
   ```bash
   cat .env | grep BOT_TOKEN
   ```

2. **Проверьте логи systemd:**
   ```bash
   sudo ./manage_bot.sh logs
   ```

3. **Проверьте логи приложения:**
   ```bash
   tail -20 logs/bot_$(date +%Y%m%d).log
   ```

4. **Убедитесь, что все зависимости установлены:**
   ```bash
   source venv/bin/activate
   pip list | grep -E "(python-telegram-bot|httpx|python-dotenv)"
   ```

### Проблема: Бот не отвечает
1. **Проверьте интернет-соединение:**
   ```bash
   ping api.telegram.org
   ```

2. **Проверьте статус сервиса:**
   ```bash
   sudo ./manage_bot.sh status
   ```

3. **Проверьте логи на ошибки:**
   ```bash
   grep -i "error\|exception" logs/bot_*.log | tail -10
   ```

### Проблема: Ошибки с правами доступа
1. **Убедитесь, что запускаете команды с sudo**
2. **Проверьте права на файлы:**
   ```bash
   ls -la .env
   ls -la bot.py
   ls -la logs/
   ```

### Проблема: Бот падает или перезапускается
1. **Проверьте логи systemd:**
   ```bash
   sudo journalctl -u meow-bot -n 50 --no-pager
   ```

2. **Проверьте использование памяти:**
   ```bash
   free -h
   ps aux | grep python | grep bot
   ```

3. **Проверьте место на диске:**
   ```bash
   df -h
   du -sh logs/
   ```

### Проблема: Логи не создаются
1. **Проверьте настройки в `.env`:**
   ```bash
   grep LOG_ .env
   ```

2. **Проверьте права на папку logs:**
   ```bash
   ls -ld logs/
   mkdir -p logs  # если папка не существует
   ```

### Проблема: Rate Limiting срабатывает неправильно
1. **Проверьте системное время:**
   ```bash
   date
   timedatectl status
   ```

2. **Перезапустите бота для сброса лимитов:**
   ```bash
   sudo ./manage_bot.sh restart
   ```

## Полезные команды

### Системные команды
```bash
# Перезагрузка systemd
sudo systemctl daemon-reload

# Проверка конфигурации сервиса
sudo systemctl cat meow-bot

# Просмотр всех логов systemd
sudo journalctl -u meow-bot --no-pager

# Очистка старых логов systemd
sudo journalctl --vacuum-time=7d
```

### Команды для работы с логами бота
```bash
# Просмотр размера всех логов
du -sh logs/

# Архивирование старых логов
tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/

# Поиск конкретных событий
grep -r "встреча" logs/
grep -r "ERROR" logs/
grep -r "пользователь.*начал" logs/

# Статистика по пользователям
grep -o "Пользователь [0-9]*" logs/bot_*.log | sort | uniq -c | sort -nr

# Мониторинг в реальном времени
tail -f logs/bot_$(date +%Y%m%d).log | grep -E "(ERROR|WARNING|встреча)"
```

### Команды для обслуживания
```bash
# Проверка целостности базы данных
sqlite3 meetings.db "PRAGMA integrity_check;"

# Резервное копирование с датой
cp meetings.db "meetings_backup_$(date +%Y%m%d_%H%M%S).db"

# Очистка временных файлов
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +

# Проверка использования портов
netstat -tulpn | grep python
lsof -i -P -n | grep python
```

## Новые возможности бота

### Функциональность встреч
- ✅ **Интерактивные кнопки** для управления встречами
- ✅ **Регулярные встречи** (6 типов повторений)
- ✅ **Гибкий ввод времени** (`15:30` или `15 30`)
- ✅ **Автоматические напоминания** с картинками котиков
- ✅ **Редактирование встреч** с возвратом в меню

### Система безопасности
- ✅ **Rate Limiting** - защита от спама
- ✅ **Валидация ввода** - ограничения длины
- ✅ **Безопасное логирование** - без персональных данных
- ✅ **Изоляция пользователей** - каждый видит только свои встречи

### Система логирования
- ✅ **Ежедневная ротация** логов
- ✅ **Автоматическая очистка** старых файлов
- ✅ **Настраиваемые параметры** через `.env`
- ✅ **Мониторинг производительности**

## Контакты для поддержки

Если у вас возникли проблемы, проверьте в следующем порядке:

1. **Логи приложения:** `tail -20 logs/bot_$(date +%Y%m%d).log`
2. **Логи systemd:** `sudo journalctl -u meow-bot -n 20`
3. **Статус сервиса:** `sudo systemctl status meow-bot`
4. **Настройки окружения:** `cat .env`
5. **Сетевые подключения:** `ping api.telegram.org`
6. **Ресурсы системы:** `free -h && df -h`

**Удачного развертывания! 🐱**

---

*Документация актуализирована для версии с модульной архитектурой, системой логирования и мерами безопасности.* 