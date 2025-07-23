import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Попытка загрузить переменные из .env файла
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получение токена бота из переменной окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("Не установлена переменная окружения BOT_TOKEN. Создайте файл .env с BOT_TOKEN=your_token или установите переменную окружения.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    await update.message.reply_text(
        "Привет! Я бот для получения картинок кошек! 🐱\n"
        "Используй команду /meow чтобы получить случайную картинку кошки."
    )

async def meow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /meow - получает и отправляет картинку кошки"""
    try:
        # Отправляем сообщение о загрузке
        # loading_message = await update.message.reply_text("Ищу кошечку для вас... 🐱")
        
        # Делаем запрос к API
        response = requests.get('https://api.thecatapi.com/v1/images/search')
        response.raise_for_status()
        
        # Получаем URL картинки
        cat_data = response.json()
        if cat_data and len(cat_data) > 0:
            image_url = cat_data[0]['url']
            
            # Отправляем картинку
            await update.message.reply_photo(
                photo=image_url,
                caption="Вот ваша кошечка! 😸"
            )
            
            # Удаляем сообщение о загрузке
            # await loading_message.delete()
        else:
            await update.message.reply_text("Извините, не удалось найти картинку кошки 😿")
            
    except requests.RequestException as e:
        logger.error(f"Ошибка при запросе к API: {e}")
        await update.message.reply_text("Извините, произошла ошибка при получении картинки 😿")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        await update.message.reply_text("Произошла неожиданная ошибка 😿")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    help_text = """
🐱 Доступные команды:

/start - Начать работу с ботом
/meow - Получить случайную картинку кошки
/help - Показать это сообщение

Бот использует API The Cat API для получения картинок кошек.
    """
    await update.message.reply_text(help_text)

def main() -> None:
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("meow", meow))
    application.add_handler(CommandHandler("help", help_command))

    # Запускаем бота
    logger.info("Бот запускается...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 