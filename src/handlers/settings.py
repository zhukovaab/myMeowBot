"""Обработчики команд для настроек пользователя"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from ..constants import SETTINGS_WAITING_REMINDER_TIME, MIN_REMINDER_MINUTES, MAX_REMINDER_MINUTES
from ..utils.helpers import format_reminder_time

logger = logging.getLogger(__name__)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать настройки пользователя"""
    from ..main import db  # Импорт здесь для избежания циклических импортов
    
    try:
        user = update.effective_user
        logger.info(f"Пользователь {user.id} запросил настройки")
        
        # Получаем текущие настройки пользователя
        user_settings = db.get_user_settings(user.id)
        reminder_minutes = user_settings['reminder_minutes']
        
        # Формируем текст с правильным склонением
        time_text = format_reminder_time(reminder_minutes)
        
        settings_text = f"""
⚙️ **Ваши настройки:**

🔔 **Время напоминания:** за {time_text} до встречи

Нажмите кнопку ниже, чтобы изменить настройки:
        """
        
        keyboard = [
            [InlineKeyboardButton("🔔 Изменить время напоминания", callback_data="change_reminder_time")],
            [InlineKeyboardButton("📋 К списку встреч", callback_data="back_to_meetings")]
        ]
        
        await update.message.reply_text(
            settings_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка при показе настроек: {e}")
        await update.message.reply_text("❌ Произошла ошибка при загрузке настроек.")


async def change_reminder_time_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало изменения времени напоминания"""
    from ..main import db  # Импорт здесь для избежания циклических импортов
    
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    logger.info(f"Пользователь {user.id} начал изменение времени напоминания")
    
    # Получаем текущие настройки
    user_settings = db.get_user_settings(user.id)
    current_minutes = user_settings['reminder_minutes']
    
    # Формируем текст с правильным склонением
    current_text = format_reminder_time(current_minutes)
    
    text = f"""
🔔 **Настройка времени напоминания**

Текущее значение: за {current_text} до встречи

Введите новое время в минутах (от {MIN_REMINDER_MINUTES} до {MAX_REMINDER_MINUTES}):

*Примеры:*
• `1` - за 1 минуту
• `5` - за 5 минут
• `15` - за 15 минут
• `30` - за 30 минут
    """
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад к настройкам", callback_data="back_to_settings")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return SETTINGS_WAITING_REMINDER_TIME


async def set_reminder_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Установка нового времени напоминания"""
    from ..main import db  # Импорт здесь для избежания циклических импортов
    
    try:
        user = update.effective_user
        text = update.message.text.strip()
        
        # Проверяем, что введено число
        try:
            minutes = int(text)
        except ValueError:
            await update.message.reply_text(
                f"❌ Пожалуйста, введите число от {MIN_REMINDER_MINUTES} до {MAX_REMINDER_MINUTES}.\n\nПример: `5`",
                parse_mode='Markdown'
            )
            return SETTINGS_WAITING_REMINDER_TIME
        
        # Проверяем диапазон
        if minutes < MIN_REMINDER_MINUTES or minutes > MAX_REMINDER_MINUTES:
            await update.message.reply_text(
                f"❌ Время напоминания должно быть от {MIN_REMINDER_MINUTES} до {MAX_REMINDER_MINUTES} минут.\n\nПример: `5`",
                parse_mode='Markdown'
            )
            return SETTINGS_WAITING_REMINDER_TIME
        
        # Сохраняем настройки
        success = db.set_user_reminder_minutes(user.id, minutes)
        
        if success:
            # Формируем текст с правильным склонением
            time_text = format_reminder_time(minutes)
            
            success_text = f"""
✅ **Настройки сохранены!**

🔔 Теперь вы будете получать напоминания за {time_text} до встречи.

Изменения вступят в силу для всех новых напоминаний.
            """
            
            keyboard = [
                [InlineKeyboardButton("⚙️ К настройкам", callback_data="back_to_settings")],
                [InlineKeyboardButton("📋 К списку встреч", callback_data="back_to_meetings")]
            ]
            
            await update.message.reply_text(
                success_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            logger.info(f"Пользователь {user.id} изменил время напоминания на {minutes} минут")
        else:
            await update.message.reply_text("❌ Произошла ошибка при сохранении настроек. Попробуйте еще раз.")
            return SETTINGS_WAITING_REMINDER_TIME
        
    except Exception as e:
        logger.error(f"Ошибка при установке времени напоминания: {e}")
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте еще раз.")
        return SETTINGS_WAITING_REMINDER_TIME
    
    return ConversationHandler.END


async def back_to_settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Возврат к настройкам"""
    from ..main import db  # Импорт здесь для избежания циклических импортов
    
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    # Получаем текущие настройки пользователя
    user_settings = db.get_user_settings(user.id)
    reminder_minutes = user_settings['reminder_minutes']
    
    # Формируем текст с правильным склонением
    time_text = format_reminder_time(reminder_minutes)
    
    settings_text = f"""
⚙️ **Ваши настройки:**

🔔 **Время напоминания:** за {time_text} до встречи

Нажмите кнопку ниже, чтобы изменить настройки:
    """
    
    keyboard = [
        [InlineKeyboardButton("🔔 Изменить время напоминания", callback_data="change_reminder_time")],
        [InlineKeyboardButton("📋 К списку встреч", callback_data="back_to_meetings")]
    ]
    
    await query.edit_message_text(
        settings_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def settings_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена настройки"""
    await update.message.reply_text("⬅️ Настройка отменена.")
    return ConversationHandler.END
