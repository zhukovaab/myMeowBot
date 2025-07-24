# My Meow Bot 🐱

Telegram бот для получения случайных картинок кошек по команде `/meow`.

## Функциональность

- `/start` - Начать работу с ботом
- `/meow` - Получить случайную картинку кошки
- `/help` - Показать справку

## Локальная разработка

### Требования

- Python 3.11+
- pip

### Установка

1. Клонируйте репозиторий:
```bash
git clone <your-repo-url>
cd my-meow-bot
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Создайте файл `.env` и добавьте токен бота:
```bash
BOT_TOKEN=your_telegram_bot_token_here
```

4. Запустите бота:
```bash
python bot.py
```

## Развертывание

### Вариант 1: Развертывание на сервере (рекомендуется)

Для развертывания на вашем собственном сервере используйте подробную инструкцию в файле [DEPLOYMENT.md](DEPLOYMENT.md).

**Быстрый старт:**
```bash
# 1. Загрузите файлы на сервер
# 2. Создайте виртуальное окружение
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Создайте файл .env с токеном
echo "BOT_TOKEN=ваш_токен_бота" > .env

# 4. Установите как systemd сервис
sudo ./manage_bot.sh install

# 5. Запустите бота
sudo ./manage_bot.sh start
```

**Управление ботом:**
```bash
sudo ./manage_bot.sh start    # Запуск
sudo ./manage_bot.sh stop     # Остановка
sudo ./manage_bot.sh restart  # Перезапуск
sudo ./manage_bot.sh status   # Статус
sudo ./manage_bot.sh logs     # Логи
```

### Вариант 2: Деплой на Render

#### Подготовка

1. Создайте аккаунт на [Render.com](https://render.com)
2. Подключите ваш GitHub/GitLab репозиторий

#### Деплой

##### Способ 1: Через render.yaml (рекомендуется)

1. Убедитесь, что файл `render.yaml` находится в корне проекта
2. Загрузите код в Git репозиторий
3. В Render Dashboard:
   - Нажмите "New +" → "Blueprint"
   - Подключите ваш репозиторий
   - Render автоматически создаст сервис на основе `render.yaml`

##### Способ 2: Ручное создание

1. В Render Dashboard нажмите "New +" → "Web Service"
2. Подключите ваш Git репозиторий
3. Настройте параметры:
   - **Name**: `my-meow-bot`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
   - **Plan**: `Free`

4. В разделе "Environment Variables" добавьте:
   - **Key**: `BOT_TOKEN`
   - **Value**: ваш токен Telegram бота

5. Нажмите "Create Web Service"

#### Обновление

При каждом push в репозиторий Render автоматически пересоберет и перезапустит приложение.

#### Мониторинг

- Логи доступны в разделе "Logs" вашего сервиса
- Статус деплоя отображается в разделе "Events"

## Получение токена бота

1. Найдите @BotFather в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Скопируйте полученный токен

## API

Бот использует [The Cat API](https://thecatapi.com/) для получения картинок кошек.

## Лицензия

MIT 