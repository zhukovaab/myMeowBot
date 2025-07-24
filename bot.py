import os
import logging
import requests
import signal
import sys
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import TimedOut, NetworkError, RetryAfter

# Попытка загрузить переменные из .env файла
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Настройка логирования для сервера
def setup_logging():
    """Настройка логирования для серверного окружения"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Настраиваем логирование только в консоль
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

setup_logging()
logger = logging.getLogger(__name__)

# Получение токена бота из переменной окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("Не установлена переменная окружения BOT_TOKEN")
    raise ValueError("Не установлена переменная окружения BOT_TOKEN. Создайте файл .env с BOT_TOKEN=your_token или установите переменную окружения.")

# Глобальная переменная для graceful shutdown
shutdown_requested = False

def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    global shutdown_requested
    logger.info(f"Получен сигнал {signum}, начинаем graceful shutdown...")
    shutdown_requested = True

# Регистрируем обработчики сигналов
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    try:
        user = update.effective_user
        logger.info(f"Пользователь {user.id} ({user.username}) запустил бота")
        
        await update.message.reply_text(
            f"Привет, {user.first_name}! Я бот для получения картинок кошек! 🐱\n"
            "Используй команду /meow чтобы получить случайную картинку кошки."
        )
    except (TimedOut, NetworkError) as e:
        logger.error(f"Ошибка сети при отправке сообщения start: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка в start: {e}")

async def meow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /meow - получает и отправляет картинку кошки"""
    user = update.effective_user
    logger.info(f"Пользователь {user.id} ({user.username}) запросил картинку кошки")
    
    loading_message = None
    try:
        # # Отправляем сообщение о загрузке
        # loading_message = await update.message.reply_text("Ищу кошечку для вас... 🐱")
        
        # Делаем запрос к API с таймаутом
        response = requests.get('https://api.thecatapi.com/v1/images/search', timeout=15)
        response.raise_for_status()
        
        # Получаем URL картинки
        cat_data = response.json()
        if cat_data and len(cat_data) > 0:
            image_url = cat_data[0]['url']
            
            # Отправляем картинку
            await update.message.reply_photo(
                photo=image_url,
            )
            
            # # Удаляем сообщение о загрузке
            # if loading_message:
            #     await loading_message.delete()
                
            logger.info(f"Картинка кошки успешно отправлена пользователю {user.id}")
        else:
            if loading_message:
                await loading_message.edit_text("Извините, не удалось найти картинку кошки 😿")
            logger.warning(f"API вернул пустой ответ для пользователя {user.id}")
            
    except requests.Timeout:
        logger.error(f"Таймаут при запросе к API кошек для пользователя {user.id}")
        if loading_message:
            await loading_message.edit_text("Извините, запрос к API занял слишком много времени 😿")
    except requests.RequestException as e:
        logger.error(f"Ошибка при запросе к API для пользователя {user.id}: {e}")
        if loading_message:
            await loading_message.edit_text("Извините, произошла ошибка при получении картинки 😿")
    except (TimedOut, NetworkError) as e:
        logger.error(f"Ошибка сети при отправке сообщения пользователю {user.id}: {e}")
        if loading_message:
            await loading_message.edit_text("Извините, проблемы с сетью 😿")
    except RetryAfter as e:
        logger.warning(f"Rate limit для пользователя {user.id}: {e}")
        if loading_message:
            await loading_message.edit_text("Слишком много запросов, попробуйте позже 😿")
    except Exception as e:
        logger.error(f"Неожиданная ошибка в meow для пользователя {user.id}: {e}")
        if loading_message:
            try:
                await loading_message.edit_text("Произошла неожиданная ошибка 😿")
            except:
                pass

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    try:
        user = update.effective_user
        logger.info(f"Пользователь {user.id} ({user.username}) запросил помощь")
        
        help_text = """
🐱 Доступные команды:

/start - Начать работу с ботом
/meow - Получить случайную картинку кошки
/help - Показать это сообщение

Бот использует API The Cat API для получения картинок кошек.
        """
        await update.message.reply_text(help_text)
    except (TimedOut, NetworkError) as e:
        logger.error(f"Ошибка сети при отправке help: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка в help: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Исключение при обработке обновления {update}: {context.error}")

def main() -> None:
    """Запуск бота"""
    try:
        logger.info("Запуск бота...")
        
        # Создаем приложение с настройками для сервера
        application = Application.builder().token(BOT_TOKEN).build()

        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("meow", meow))
        application.add_handler(CommandHandler("help", help_command))
        
        # Добавляем обработчик ошибок
        application.add_error_handler(error_handler)

        # Запускаем бота с настройками для сервера
        logger.info("Бот успешно запущен и готов к работе!")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            timeout=30,
            read_timeout=30,
            write_timeout=30,
            drop_pending_updates=True  # Игнорируем старые сообщения при запуске
        )
        
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания, завершаем работу...")
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")
        raise
    finally:
        logger.info("Бот завершил работу")

if __name__ == '__main__':
    main() 