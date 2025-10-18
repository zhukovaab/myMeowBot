"""Обработчики команд для работы с встречами"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from ..constants import (
    WAITING_TITLE, WAITING_DESCRIPTION, WAITING_TIME,
    EDIT_WAITING_CHOICE, EDIT_WAITING_TITLE, EDIT_WAITING_DESCRIPTION, 
    EDIT_WAITING_TIME, EDIT_WAITING_RECURRENCE, EDIT_WAITING_END_DATE,
    MAX_TITLE_LENGTH, MAX_DESCRIPTION_LENGTH, MAX_MEETINGS_PER_DAY
)
from ..utils.helpers import parse_datetime, format_reminder_time, format_recurrence_info, format_meeting_time_for_user
from ..utils.rate_limiter import check_rate_limit, get_remaining_quota

logger = logging.getLogger(__name__)


async def add_meeting_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало добавления встречи"""
    user = update.effective_user
    
    # Проверяем rate limit
    allowed, remaining = check_rate_limit(user.id, "meeting")
    if not allowed:
        await update.message.reply_text(
            f"❌ Вы достигли дневного лимита создания встреч ({MAX_MEETINGS_PER_DAY} встреч в день).\n"
            "Попробуйте завтра!"
        )
        return ConversationHandler.END
    
    logger.info(f"Пользователь {user.id} начал добавление встречи (осталось: {remaining})")
    
    await update.message.reply_text(
        f"📝 Добавление новой встречи\n\n"
        f"Введите название встречи:\n\n"
        f"💡 Осталось встреч сегодня: {remaining}"
    )
    return WAITING_TITLE


async def add_meeting_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение названия встречи"""
    title = update.message.text.strip()
    
    # Проверка на пустоту
    if not title:
        await update.message.reply_text("❌ Название не может быть пустым. Попробуйте еще раз:")
        return WAITING_TITLE
    
    # Проверка длины
    if len(title) > MAX_TITLE_LENGTH:
        await update.message.reply_text(
            f"❌ Название слишком длинное (максимум {MAX_TITLE_LENGTH} символов).\n"
            f"Текущая длина: {len(title)} символов. Попробуйте еще раз:"
        )
        return WAITING_TITLE
    
    context.user_data['meeting_title'] = title
    await update.message.reply_text(
        "📄 Введите описание встречи (или отправьте '-' чтобы пропустить):"
    )
    return WAITING_DESCRIPTION


async def add_meeting_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение описания встречи"""
    description = update.message.text.strip()
    
    # Если пользователь отправил '-', пропускаем описание
    if description == '-':
        description = ""
    elif description and len(description) > MAX_DESCRIPTION_LENGTH:
        # Проверка длины описания
        await update.message.reply_text(
            f"❌ Описание слишком длинное (максимум {MAX_DESCRIPTION_LENGTH} символов).\n"
            f"Текущая длина: {len(description)} символов. Попробуйте еще раз или отправьте '-' чтобы пропустить:"
        )
        return WAITING_DESCRIPTION
    
    context.user_data['meeting_description'] = description
    await update.message.reply_text(
        "🕐 Введите дату и время встречи в одном из форматов:\n\n"
        "• `15:30` или `15 30` - сегодня в указанное время (если не прошло) или завтра\n"
        "• `завтра 10:00` или `завтра 10 00` - завтра в 10:00\n"
        "• `25.12 14:00` или `25.12 14 00` - 25 декабря в 14:00\n"
        "• `25.12.2024 14:00` или `25.12.2024 14 00` - 25 декабря 2024 года в 14:00",
        parse_mode='Markdown'
    )
    return WAITING_TIME


async def add_meeting_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение времени встречи и сохранение"""
    from ..main import db  # Импорт здесь для избежания циклических импортов
    
    user = update.effective_user
    time_str = update.message.text.strip()
    
    try:
        # Получаем часовой пояс пользователя
        user_timezone = db.get_user_timezone(user.id)
        meeting_time = parse_datetime(time_str, user_timezone)
        
        # Проверяем, что время в будущем (сравниваем в UTC)
        if meeting_time <= datetime.utcnow():
            await update.message.reply_text(
                "⚠️ Время встречи должно быть в будущем. Попробуйте еще раз:"
            )
            return WAITING_TIME
        
        # Сохраняем встречу
        title = context.user_data['meeting_title']
        description = context.user_data['meeting_description']
        
        meeting_id = db.add_meeting(user.id, title, description, meeting_time)
        
        # Форматируем время для отображения в часовом поясе пользователя
        user_timezone = db.get_user_timezone(user.id)
        time_display = format_meeting_time_for_user(meeting_time, user_timezone)
        
        # Получаем пользовательские настройки времени напоминания
        user_reminder_minutes = db.get_user_reminder_minutes(user.id)
        reminder_text = format_reminder_time(user_reminder_minutes)
        logger.info(f"Пользователь {user.id}: время напоминания {user_reminder_minutes} минут")
        
        await update.message.reply_text(
            f"✅ Встреча успешно добавлена!\n\n"
            f"📝 Название: {title}\n"
            f"📄 Описание: {description if description else 'Не указано'}\n"
            f"🕐 Время: {time_display}\n"
            f"🆔 ID встречи: {meeting_id}\n\n"
            f"🔔 Я напомню вам за {reminder_text} до начала!"
        )
        
        # Очищаем данные
        context.user_data.clear()
        
        logger.info(f"Пользователь {user.id} добавил встречу ID {meeting_id} на {meeting_time}")
        return ConversationHandler.END
        
    except ValueError as e:
        await update.message.reply_text(
            f"⚠️ Ошибка в формате времени: {str(e)}\n\n"
            "Попробуйте еще раз в одном из форматов:\n"
            "• `15:30` или `15 30`\n"
            "• `завтра 10:00` или `завтра 10 00`\n"
            "• `25.12 14:00` или `25.12 14 00`\n"
            "• `25.12.2024 14:00` или `25.12.2024 14 00`",
            parse_mode='Markdown'
        )
        return WAITING_TIME


async def add_meeting_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена добавления встречи"""
    context.user_data.clear()
    await update.message.reply_text("❌ Добавление встречи отменено.")
    return ConversationHandler.END


async def list_meetings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать список встреч пользователя"""
    from ..main import db  # Импорт здесь для избежания циклических импортов
    
    user = update.effective_user
    logger.info(f"Пользователь {user.id} запросил список встреч")
    
    try:
        meetings = db.get_user_meetings(user.id)
        
        if not meetings:
            # Создаем кнопки для добавления встреч
            keyboard = [
                [InlineKeyboardButton("➕ Добавить встречу", callback_data="action_add")],
                [InlineKeyboardButton("⚙️ Настройки", callback_data="back_to_settings")]
            ]
            
            await update.message.reply_text(
                "📅 У вас пока нет запланированных встреч.\n\n"
                "Используйте /add_meeting чтобы добавить новую встречу.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        # Получаем часовой пояс пользователя
        user_timezone = db.get_user_timezone(user.id)
        
        # Разделяем встречи на прошедшие и предстоящие
        now_utc = datetime.utcnow()
        upcoming = []
        past = []
        
        for meeting in meetings:
            meeting_time = datetime.fromisoformat(meeting['meeting_time'])
            if meeting_time > now_utc:
                upcoming.append((meeting, meeting_time))
            else:
                past.append((meeting, meeting_time))
        
        response = "📅 **Ваши встречи:**\n\n"
        
        # Предстоящие встречи
        if upcoming:
            response += "🔜 **Предстоящие:**\n"
            for meeting, meeting_time in upcoming:
                time_str = format_meeting_time_for_user(meeting_time, user_timezone)
                
                # Иконка для регулярных встреч
                icon = "🔄" if meeting.get('is_recurring') else "📅"
                
                response += f"• `{meeting['id']}` {icon} {meeting['title']}\n"
                response += f"  🕐 {time_str}\n"
                
                if meeting['description']:
                    response += f"  📄 {meeting['description']}\n"
                
                # Информация о регулярности
                if meeting.get('is_recurring'):
                    recurrence_text = format_recurrence_info(meeting)
                    response += f"  🔄 Повторяется: {recurrence_text}\n"
                    
                    # Дата окончания
                    if meeting.get('recurrence_end_date'):
                        end_date = datetime.fromisoformat(meeting['recurrence_end_date'])
                        end_str = end_date.strftime("%d.%m.%Y")
                        response += f"  🏁 До: {end_str}\n"
                
                response += "\n"
        
        # Прошедшие встречи (последние 5)
        if past:
            response += "📋 **Прошедшие (последние 5):**\n"
            for meeting, meeting_time in past[-5:]:
                time_str = format_meeting_time_for_user(meeting_time, user_timezone)
                response += f"• `{meeting['id']}` - {meeting['title']}\n"
                response += f"  🕐 {time_str}\n"
                response += "\n"
        
        # Создаем основные кнопки управления
        keyboard = [
            [InlineKeyboardButton("➕ Добавить встречу", callback_data="action_add")],
        ]
        
        # Добавляем кнопки редактирования и удаления только если есть встречи
        if upcoming:
            keyboard.extend([
                [InlineKeyboardButton("✏️ Редактировать встречу", callback_data="action_edit_list")],
                [InlineKeyboardButton("🗑️ Удалить встречу", callback_data="action_delete_list")]
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(response, parse_mode='Markdown', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Ошибка при получении списка встреч для пользователя {user.id}: {e}")
        await update.message.reply_text("❌ Произошла ошибка при получении списка встреч.")


async def delete_meeting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Удаление встречи"""
    from ..main import db  # Импорт здесь для избежания циклических импортов
    
    user = update.effective_user
    logger.info(f"Пользователь {user.id} запросил удаление встречи")
    
    args = context.args
    if not args:
        await update.message.reply_text(
            "❌ Укажите ID встречи для удаления.\n\n"
            "Пример: `/delete_meeting 123`\n"
            "ID можно узнать командой /meetings",
            parse_mode='Markdown'
        )
        return
    
    try:
        meeting_id = int(args[0])
        
        # Проверяем, что встреча существует и принадлежит пользователю
        meeting = db.get_meeting_by_id(meeting_id, user.id)
        if not meeting:
            await update.message.reply_text(
                f"❌ Встреча с ID {meeting_id} не найдена или не принадлежит вам."
            )
            return
        
        # Создаем кнопки подтверждения
        keyboard = [
            [
                InlineKeyboardButton("✅ Да, удалить", callback_data=f"delete_confirm_{meeting_id}"),
                InlineKeyboardButton("📋 К списку встреч", callback_data="back_to_meetings")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        meeting_time = datetime.fromisoformat(meeting['meeting_time'])
        user_timezone = db.get_user_timezone(user.id)
        time_str = format_meeting_time_for_user(meeting_time, user_timezone)
        
        await update.message.reply_text(
            f"🗑️ **Удаление встречи**\n\n"
            f"📝 Название: {meeting['title']}\n"
            f"🕐 Время: {time_str}\n\n"
            f"Вы уверены, что хотите удалить эту встречу?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except ValueError:
        await update.message.reply_text("❌ Неверный ID встречи. Должно быть число.")
