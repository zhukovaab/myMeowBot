"""Обработчики для редактирования встреч"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from ..constants import (
    EDIT_WAITING_CHOICE, EDIT_WAITING_TITLE, EDIT_WAITING_DESCRIPTION, 
    EDIT_WAITING_TIME, EDIT_WAITING_RECURRENCE, EDIT_WAITING_END_DATE,
    MAX_TITLE_LENGTH, MAX_DESCRIPTION_LENGTH
)
from ..utils.helpers import parse_datetime, format_reminder_time, format_recurrence_info

logger = logging.getLogger(__name__)


async def show_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, meeting_id: int, user_id: int) -> int:
    """Показать меню редактирования встречи"""
    from ..main import db
    
    # Получаем обновленную информацию о встрече
    meeting = db.get_meeting_by_id(meeting_id, user_id)
    if not meeting:
        await update.message.reply_text("❌ Встреча не найдена.")
        context.user_data.clear()
        return ConversationHandler.END
    
    # Форматируем информацию о встрече
    meeting_time = datetime.fromisoformat(meeting['meeting_time'])
    time_str = meeting_time.strftime("%d.%m.%Y в %H:%M")
    
    text = f"✏️ **Редактирование встречи**\n\n"
    text += f"📝 **Название:** {meeting['title']}\n"
    text += f"📄 **Описание:** {meeting['description'] if meeting['description'] else 'Не указано'}\n"
    text += f"🕐 **Время:** {time_str}\n"
    
    # Информация о регулярности
    if meeting.get('is_recurring'):
        recurrence_text = format_recurrence_info(meeting)
        text += f"🔄 **Повторяется:** {recurrence_text}\n"
        
        if meeting.get('recurrence_end_date'):
            end_date = datetime.fromisoformat(meeting['recurrence_end_date'])
            end_str = end_date.strftime("%d.%m.%Y")
            text += f"🏁 **До:** {end_str}\n"
    
    text += "\n**Что хотите изменить?**"
    
    # Создаем кнопки для выбора что редактировать
    keyboard = [
        [InlineKeyboardButton("📝 Название", callback_data="edit_title")],
        [InlineKeyboardButton("📄 Описание", callback_data="edit_description")],
        [InlineKeyboardButton("🕐 Время", callback_data="edit_time")],
    ]
    
    # Добавляем кнопки для регулярных встреч
    if meeting.get('is_recurring'):
        keyboard.extend([
            [InlineKeyboardButton("🔄 Настройки повторения", callback_data="edit_recurrence")],
            [InlineKeyboardButton("🏁 Дата окончания", callback_data="edit_end_date")]
        ])
    
    keyboard.extend([
        [InlineKeyboardButton("🗑️ Удалить встречу", callback_data=f"delete_confirm_{meeting_id}")],
        [InlineKeyboardButton("⬅️ Назад к списку", callback_data="back_to_meetings")]
    ])
    
    # Отправляем новое сообщение с меню
    await update.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return EDIT_WAITING_CHOICE


async def edit_meeting_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало редактирования встречи через callback"""
    from ..main import db  # Импорт здесь для избежания циклических импортов
    
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    # Извлекаем ID встречи из callback_data
    meeting_id = int(query.data.split("_")[1])
    
    # Получаем встречу из базы данных
    meeting = db.get_meeting_by_id(meeting_id, user.id)
    if not meeting:
        await query.edit_message_text("❌ Встреча не найдена или не принадлежит вам.")
        return ConversationHandler.END
    
    # Сохраняем ID встречи в контексте
    context.user_data['editing_meeting_id'] = meeting_id
    
    # Форматируем информацию о встрече
    meeting_time = datetime.fromisoformat(meeting['meeting_time'])
    time_str = meeting_time.strftime("%d.%m.%Y в %H:%M")
    
    text = f"✏️ **Редактирование встречи**\n\n"
    text += f"📝 **Название:** {meeting['title']}\n"
    text += f"📄 **Описание:** {meeting['description'] if meeting['description'] else 'Не указано'}\n"
    text += f"🕐 **Время:** {time_str}\n"
    
    # Информация о регулярности
    if meeting.get('is_recurring'):
        recurrence_text = format_recurrence_info(meeting)
        text += f"🔄 **Повторяется:** {recurrence_text}\n"
        
        if meeting.get('recurrence_end_date'):
            end_date = datetime.fromisoformat(meeting['recurrence_end_date'])
            end_str = end_date.strftime("%d.%m.%Y")
            text += f"🏁 **До:** {end_str}\n"
    
    text += "\n**Что хотите изменить?**"
    
    # Создаем кнопки для выбора что редактировать
    keyboard = [
        [InlineKeyboardButton("📝 Название", callback_data="edit_title")],
        [InlineKeyboardButton("📄 Описание", callback_data="edit_description")],
        [InlineKeyboardButton("🕐 Время", callback_data="edit_time")],
    ]
    
    # Добавляем кнопки для регулярных встреч
    if meeting.get('is_recurring'):
        keyboard.extend([
            [InlineKeyboardButton("🔄 Настройки повторения", callback_data="edit_recurrence")],
            [InlineKeyboardButton("🏁 Дата окончания", callback_data="edit_end_date")]
        ])
    
    keyboard.extend([
        [InlineKeyboardButton("🗑️ Удалить встречу", callback_data=f"delete_confirm_{meeting_id}")],
        [InlineKeyboardButton("⬅️ Назад к списку", callback_data="back_to_meetings")]
    ])
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    logger.info(f"Пользователь {user.id} начал редактирование встречи ID {meeting_id}")
    return EDIT_WAITING_CHOICE


async def edit_choice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора что редактировать"""
    query = update.callback_query
    await query.answer()
    
    choice = query.data
    
    if choice == "edit_title":
        await query.edit_message_text(
            "📝 **Редактирование названия**\n\n"
            "Введите новое название встречи:",
            parse_mode='Markdown'
        )
        return EDIT_WAITING_TITLE
    
    elif choice == "edit_description":
        await query.edit_message_text(
            "📄 **Редактирование описания**\n\n"
            "Введите новое описание встречи (или '-' чтобы убрать описание):",
            parse_mode='Markdown'
        )
        return EDIT_WAITING_DESCRIPTION
    
    elif choice == "edit_time":
        await query.edit_message_text(
            "🕐 **Редактирование времени**\n\n"
            "Введите новое время встречи в одном из форматов:\n\n"
            "• `15:30` или `15 30` - сегодня в указанное время (если не прошло) или завтра\n"
            "• `завтра 10:00` или `завтра 10 00` - завтра в 10:00\n"
            "• `25.12 14:00` или `25.12 14 00` - 25 декабря в 14:00\n"
            "• `25.12.2024 14:00` или `25.12.2024 14 00` - 25 декабря 2024 года в 14:00",
            parse_mode='Markdown'
        )
        return EDIT_WAITING_TIME
    
    elif choice == "edit_recurrence":
        await query.edit_message_text(
            "🔄 **Редактирование повторения**\n\n"
            "Эта функция пока в разработке. Используйте кнопку 'Назад' для возврата.",
            parse_mode='Markdown'
        )
        return EDIT_WAITING_RECURRENCE
    
    elif choice == "edit_end_date":
        await query.edit_message_text(
            "🏁 **Редактирование даты окончания**\n\n"
            "Введите новую дату окончания повторений в формате:\n"
            "• `25.12` - 25 декабря текущего года\n"
            "• `25.12.2024` - 25 декабря 2024 года\n"
            "• `-` - убрать дату окончания (бесконечные повторения)",
            parse_mode='Markdown'
        )
        return EDIT_WAITING_END_DATE
    
    return ConversationHandler.END


async def edit_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обновление названия встречи"""
    from ..main import db
    
    user = update.effective_user
    new_title = update.message.text.strip()
    
    if not new_title:
        await update.message.reply_text("❌ Название не может быть пустым. Попробуйте еще раз:")
        return EDIT_WAITING_TITLE
    
    if len(new_title) > MAX_TITLE_LENGTH:
        await update.message.reply_text(
            f"❌ Название слишком длинное (максимум {MAX_TITLE_LENGTH} символов).\n"
            f"Текущая длина: {len(new_title)} символов. Попробуйте еще раз:"
        )
        return EDIT_WAITING_TITLE
    
    meeting_id = context.user_data.get('editing_meeting_id')
    if not meeting_id:
        await update.message.reply_text("❌ Ошибка: встреча не найдена.")
        return ConversationHandler.END
    
    # Обновляем встречу
    success = db.update_meeting(meeting_id, user.id, title=new_title)
    
    if success:
        await update.message.reply_text(f"✅ Название встречи обновлено на: **{new_title}**", parse_mode='Markdown')
        logger.info(f"Пользователь {user.id} обновил название встречи ID {meeting_id}")
        
        # Возвращаемся к меню редактирования встречи
        return await show_edit_menu(update, context, meeting_id, user.id)
    else:
        await update.message.reply_text("❌ Ошибка при обновлении встречи.")
        context.user_data.clear()
        return ConversationHandler.END


async def edit_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обновление описания встречи"""
    from ..main import db
    
    user = update.effective_user
    new_description = update.message.text.strip()
    
    if new_description == '-':
        new_description = ""
    elif new_description and len(new_description) > MAX_DESCRIPTION_LENGTH:
        await update.message.reply_text(
            f"❌ Описание слишком длинное (максимум {MAX_DESCRIPTION_LENGTH} символов).\n"
            f"Текущая длина: {len(new_description)} символов. Попробуйте еще раз или отправьте '-' для пустого описания:"
        )
        return EDIT_WAITING_DESCRIPTION
    
    meeting_id = context.user_data.get('editing_meeting_id')
    if not meeting_id:
        await update.message.reply_text("❌ Ошибка: встреча не найдена.")
        return ConversationHandler.END
    
    # Обновляем встречу
    success = db.update_meeting(meeting_id, user.id, description=new_description)
    
    if success:
        if new_description:
            await update.message.reply_text(f"✅ Описание встречи обновлено на: **{new_description}**", parse_mode='Markdown')
        else:
            await update.message.reply_text("✅ Описание встречи удалено.")
        logger.info(f"Пользователь {user.id} обновил описание встречи ID {meeting_id}")
        
        # Возвращаемся к меню редактирования встречи
        return await show_edit_menu(update, context, meeting_id, user.id)
    else:
        await update.message.reply_text("❌ Ошибка при обновлении встречи.")
        context.user_data.clear()
        return ConversationHandler.END


async def edit_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обновление времени встречи"""
    from ..main import db
    
    user = update.effective_user
    time_str = update.message.text.strip()
    
    try:
        new_time = parse_datetime(time_str)
        
        # Проверяем, что время в будущем
        if new_time <= datetime.now():
            await update.message.reply_text(
                "⚠️ Время встречи должно быть в будущем. Попробуйте еще раз:"
            )
            return EDIT_WAITING_TIME
        
        meeting_id = context.user_data.get('editing_meeting_id')
        if not meeting_id:
            await update.message.reply_text("❌ Ошибка: встреча не найдена.")
            return ConversationHandler.END
        
        # Обновляем встречу
        success = db.update_meeting(meeting_id, user.id, meeting_time=new_time)
        
        if success:
            time_display = new_time.strftime("%d.%m.%Y в %H:%M")
            await update.message.reply_text(f"✅ Время встречи обновлено на: **{time_display}**", parse_mode='Markdown')
            logger.info(f"Пользователь {user.id} обновил время встречи ID {meeting_id} на {new_time}")
            
            # Возвращаемся к меню редактирования встречи
            return await show_edit_menu(update, context, meeting_id, user.id)
        else:
            await update.message.reply_text("❌ Ошибка при обновлении встречи.")
            context.user_data.clear()
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
        return EDIT_WAITING_TIME


async def edit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена редактирования встречи"""
    context.user_data.clear()
    await update.message.reply_text("❌ Редактирование встречи отменено.")
    return ConversationHandler.END


async def back_to_edit_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Возврат к списку встреч для редактирования"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    # Очищаем контекст редактирования
    context.user_data.clear()
    
    # Показываем список встреч для редактирования
    from .callbacks import show_meetings_for_action
    await show_meetings_for_action(query, user.id, "edit", "✏️ Выберите встречу для редактирования:")
    
    return ConversationHandler.END
