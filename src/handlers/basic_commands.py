"""Обработчики основных команд бота"""

import logging
import requests
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import TimedOut, NetworkError, RetryAfter

from ..constants import CAT_API_URL, REQUEST_TIMEOUT

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    try:
        user = update.effective_user
        logger.info(f"Пользователь {user.id} ({user.username}) запустил бота")
        
        start_text = f"""Привет, {user.first_name}! 🐱 

Я многофункциональный бот для управления встречами и получения картинок кошек!

🐱 Основные команды:
/start - Начать работу с ботом
/meow - Получить случайную картинку кошки
/help - Подробная справка

📅 Управление встречами:
/meetings - Показать список встреч
/add_meeting - Добавить разовую встречу
/add_recurring - Добавить регулярную встречу
/edit_meeting - Редактировать встречу
/delete_meeting - Удалить встречу

⚙️ Настройки:
/settings - Настройки напоминаний и часового пояса

🔔 Возможности:
• Получение картинок котиков 🐱
• Напоминания за настраиваемое время
• Регулярные встречи (ежедневно, еженедельно, по будням, по выбранным дням)
• Поддержка часовых поясов
• Автоматическое удаление прошедших встреч
• Редактирование всех параметров встреч

Для подробной справки используй /help"""
        
        await update.message.reply_text(start_text)
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
        # Делаем запрос к API с таймаутом
        response = requests.get(CAT_API_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        # Получаем URL картинки
        cat_data = response.json()
        if cat_data and len(cat_data) > 0:
            image_url = cat_data[0]['url']
            
            # Отправляем картинку
            await update.message.reply_photo(photo=image_url)
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
        
        help_text = """🐱 Доступные команды:

Основные:
/start - Начать работу с ботом
/meow - Получить случайную картинку кошки
/help - Показать это сообщение

Встречи:
/add_meeting - Добавить разовую встречу
/add_recurring - Добавить регулярную встречу
/meetings - Показать список встреч
/edit_meeting - Редактировать встречу
/delete_meeting - Удалить встречу

Настройки:
/settings - Настройки напоминаний

Особенности:
🔔 Настраиваемое время напоминаний (по умолчанию за 2 минуты)
🗑️ Автоматическое удаление прошедших встреч
🔄 Поддержка регулярных встреч (ежедневно, еженедельно, ежемесячно)
⏰ Поддержка ввода времени через пробел: 15 30 или 15:30"""
        
        await update.message.reply_text(help_text)
    except (TimedOut, NetworkError) as e:
        logger.error(f"Ошибка сети при отправке help: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка в help: {e}")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Исключение при обработке обновления {update}: {context.error}")
