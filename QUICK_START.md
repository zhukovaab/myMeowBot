# Быстрый старт - Развертывание Meow Bot

## Минимальные требования
- Ubuntu/Debian сервер
- Python 3.8+
- sudo права

## Пошаговая инструкция (5 минут)

### 1. Подготовка сервера
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv git -y
```

### 2. Загрузка проекта
```bash
git clone <ваш-репозиторий> my-meow-bot
cd my-meow-bot
```

### 3. Настройка Python
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Настройка токена
```bash
nano .env
```
Добавьте: `BOT_TOKEN=ваш_токен_бота`

### 5. Тестирование
```bash
python bot.py
```
Нажмите Ctrl+C для остановки

### 6. Установка как сервис
```bash
chmod +x manage_bot.sh
sudo ./manage_bot.sh install
sudo ./manage_bot.sh start
```

### 7. Проверка работы
```bash
sudo ./manage_bot.sh status
```

## Готово! 🎉

Ваш бот теперь работает как системный сервис и будет автоматически запускаться при перезагрузке сервера.

## Управление
```bash
sudo ./manage_bot.sh start    # Запуск
sudo ./manage_bot.sh stop     # Остановка  
sudo ./manage_bot.sh restart  # Перезапуск
sudo ./manage_bot.sh status   # Статус
sudo ./manage_bot.sh logs     # Логи
```

## Получение токена бота
1. Найдите @BotFather в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте токен

## Подробная инструкция
См. [DEPLOYMENT.md](DEPLOYMENT.md) для детального описания всех шагов и устранения неполадок. 