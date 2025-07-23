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

## Деплой на Fly.io

### Подготовка

1. Установите Fly CLI:
```bash
# macOS
brew install flyctl

# Linux
curl -L https://fly.io/install.sh | sh
```

2. Войдите в аккаунт Fly.io:
```bash
fly auth login
```

### Деплой

1. Создайте приложение на Fly.io:
```bash
fly apps create my-meow-bot
```

2. Установите секрет с токеном бота:
```bash
fly secrets set BOT_TOKEN=your_telegram_bot_token_here
```

3. Разверните приложение:
```bash
fly deploy
```

4. Проверьте статус:
```bash
fly status
```

### Обновление

Для обновления бота просто выполните:
```bash
fly deploy
```

## Получение токена бота

1. Найдите @BotFather в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Скопируйте полученный токен

## API

Бот использует [The Cat API](https://thecatapi.com/) для получения картинок кошек.

## Лицензия

MIT 