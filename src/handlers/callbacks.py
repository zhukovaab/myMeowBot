"""Обработчики callback запросов"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ..utils.helpers import format_meeting_time_for_user

logger = logging.getLogger(__name__)


async def add_meeting_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка callback для начала добавления встречи"""
    from ..constants import WAITING_TITLE, RECURRING_WAITING_TITLE
    
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    logger.info(f"Пользователь {user.id} начал добавление встречи через callback")
    
    if query.data == "add_regular":
        await query.edit_message_text(
            "📝 Добавление новой встречи\n\n"
            "Введите название встречи:"
        )
        return WAITING_TITLE
    elif query.data == "add_recurring":
        await query.edit_message_text(
            "🔄 Добавление регулярной встречи\n\n"
            "Введите название встречи:"
        )
        return RECURRING_WAITING_TITLE


async def delete_meeting_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка подтверждения удаления встречи"""
    from ..main import db  # Импорт здесь для избежания циклических импортов
    
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    if query.data == "back_to_meetings":
        await show_main_meetings_list(query, user.id)
        return
    
    if query.data.startswith("delete_confirm_"):
        meeting_id = int(query.data.split("_")[2])
        
        if db.delete_meeting(meeting_id, user.id):
            await query.edit_message_text(f"✅ Встреча ID {meeting_id} успешно удалена.")
            logger.info(f"Пользователь {user.id} удалил встречу ID {meeting_id}")
        else:
            await query.edit_message_text("❌ Ошибка при удалении встречи.")


async def meetings_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка действий из списка встреч"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    if query.data == "action_add":
        # Перенаправляем на добавление встречи
        await query.edit_message_text(
            "➕ Выберите тип встречи:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📅 Обычная встреча", callback_data="add_regular")],
                [InlineKeyboardButton("🔄 Регулярная встреча", callback_data="add_recurring")],
                [InlineKeyboardButton("📋 К списку встреч", callback_data="back_to_meetings")]
            ])
        )
        return
    
    elif query.data == "add_regular":
        # Начинаем процесс добавления обычной встречи
        await query.edit_message_text(
            "📝 Добавление новой встречи\n\n"
            "Введите название встречи:"
        )
        return
    
    elif query.data == "add_recurring":
        # Начинаем процесс добавления регулярной встречи  
        await query.edit_message_text(
            "🔄 Добавление регулярной встречи\n\n"
            "Введите название встречи:"
        )
        return
    
    elif query.data == "action_edit_list":
        # Показываем список встреч для редактирования
        await show_meetings_for_action(query, user.id, "edit", "✏️ Выберите встречу для редактирования:")
        return
    
    elif query.data == "action_delete_list":
        # Показываем список встреч для удаления
        await show_meetings_for_action(query, user.id, "delete", "🗑️ Выберите встречу для удаления:")
        return
    
    elif query.data == "back_to_meetings":
        # Возвращаемся к основному списку встреч
        await show_main_meetings_list(query, user.id)
        return


async def show_meetings_for_action(query, user_id: int, action: str, title: str):
    """Показывает список встреч для выбранного действия (редактирование/удаление)"""
    from ..main import db  # Импорт здесь для избежания циклических импортов
    
    try:
        meetings = db.get_user_meetings(user_id)
        
        if not meetings:
            await query.edit_message_text(
                "📭 У вас пока нет встреч.\n\n"
                "Нажмите ➕ Добавить встречу, чтобы создать первую встречу.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Добавить встречу", callback_data="action_add")],
                    [InlineKeyboardButton("📋 К списку встреч", callback_data="back_to_meetings")]
                ])
            )
            return
        
        # Сортируем встречи по времени (сравниваем в UTC)
        now_utc = datetime.utcnow()
        upcoming = []
        
        for meeting in meetings:
            meeting_time = datetime.fromisoformat(meeting['meeting_time'])
            if meeting_time > now_utc:
                upcoming.append((meeting, meeting_time))
        
        upcoming.sort(key=lambda x: x[1])
        
        if not upcoming:
            await query.edit_message_text(
                "📭 У вас нет предстоящих встреч.\n\n"
                "Все встречи уже прошли.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("➕ Добавить встречу", callback_data="action_add")],
                    [InlineKeyboardButton("📋 К списку встреч", callback_data="back_to_meetings")]
                ])
            )
            return
        
        # Формируем только кнопки без дублирования текста
        text = f"{title}\n\n"
        keyboard = []
        
        # Получаем часовой пояс пользователя
        user_timezone = db.get_user_timezone(user_id)
        
        for meeting, meeting_time in upcoming[:10]:  # Показываем максимум 10 встреч
            meeting_id = meeting['id']
            title_short = meeting['title'][:25] + "..." if len(meeting['title']) > 25 else meeting['title']
            # Для кнопок используем короткий формат без года (если текущий год)
            time_display = format_meeting_time_for_user(meeting_time, user_timezone)
            current_year = str(datetime.now().year)
            if f".{current_year}" in time_display:
                time_str = time_display.replace(f".{current_year}", "")
            else:
                time_str = time_display
            
            # Добавляем иконку для регулярных встреч
            icon = "🔄" if meeting.get('is_recurring') else "📅"
            
            # Создаем кнопку с информацией о встрече
            button_text = f"{icon} {title_short} ({time_str})"
            
            if action == "edit":
                keyboard.append([InlineKeyboardButton(button_text, callback_data=f"edit_{meeting_id}")])
            elif action == "delete":
                keyboard.append([InlineKeyboardButton(f"🗑️ {title_short} ({time_str})", callback_data=f"delete_confirm_{meeting_id}")])
        
        # Добавляем кнопку возврата
        keyboard.append([InlineKeyboardButton("⬅️ Назад к списку", callback_data="back_to_meetings")])
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Ошибка при показе списка встреч для действия {action}: {e}")
        await query.edit_message_text(
            "❌ Произошла ошибка при получении списка встреч.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 К списку встреч", callback_data="back_to_meetings")]
            ])
        )


async def show_main_meetings_list(update_or_query, user_id: int):
    """Показывает основной список встреч (как команда /meetings)"""
    from ..main import db  # Импорт здесь для избежания циклических импортов
    from ..utils.helpers import format_recurrence_info
    
    try:
        meetings = db.get_user_meetings(user_id)
        
        if not meetings:
            response = "📭 У вас пока нет встреч.\n\n"
            response += "Используйте кнопку ниже, чтобы добавить первую встречу!"
        else:
            # Сортируем встречи по времени (сравниваем в UTC)
            now_utc = datetime.utcnow()
            upcoming = []
            
            for meeting in meetings:
                meeting_time = datetime.fromisoformat(meeting['meeting_time'])
                # Предстоящие встречи: будущие встречи ИЛИ регулярные встречи (которые автоматически обновляются)
                if meeting_time > now_utc or meeting.get('is_recurring'):
                    upcoming.append((meeting, meeting_time))
            
            upcoming.sort(key=lambda x: x[1])
            
            # Разделяем встречи на прошедшие и предстоящие
            # Регулярные встречи не попадают в прошедшие, так как они автоматически обновляются
            past = []
            for meeting in meetings:
                meeting_time = datetime.fromisoformat(meeting['meeting_time'])
                # Только обычные встречи могут быть прошедшими
                if meeting_time <= now_utc and not meeting.get('is_recurring'):
                    past.append((meeting, meeting_time))
            
            response = "📅 **Ваши встречи:**\n\n"
            
            # Предстоящие встречи
            if upcoming:
                response += "🔜 **Предстоящие:**\n"
                # Получаем часовой пояс пользователя
                user_timezone = db.get_user_timezone(user_id)
                
                for meeting, meeting_time in upcoming:
                    time_str = format_meeting_time_for_user(meeting_time, user_timezone)
                    
                    # Иконка для регулярных встреч
                    icon = "🔄" if meeting.get('is_recurring') else "📅"
                    
                    response += f"• `{meeting['id']}` {icon} {meeting['title']}\n"
                    response += f"  🕐 {time_str}\n"
                    
                    if meeting['description']:
                        response += f"  📄 {meeting['description']}\n"
                    
                    # Информация о регулярности (упрощенная версия)
                    if meeting.get('is_recurring'):
                        recurrence_text = format_recurrence_info(meeting)
                        response += f"  🔄 {recurrence_text}\n"
                    
                    response += "\n"
            else:
                response += "📭 Нет предстоящих встреч.\n\n"
            
            # Прошедшие встречи (показываем только количество)
            if past:
                response += f"📋 Прошедших встреч: {len(past)}\n\n"
        
        # Создаем основные кнопки управления
        keyboard = [
            [InlineKeyboardButton("➕ Добавить встречу", callback_data="action_add")],
        ]
        
        # Добавляем кнопки редактирования и удаления только если есть встречи
        if meetings:
            keyboard.extend([
                [InlineKeyboardButton("✏️ Редактировать встречу", callback_data="action_edit_list")],
                [InlineKeyboardButton("🗑️ Удалить встречу", callback_data="action_delete_list")]
            ])
        
        if hasattr(update_or_query, 'edit_message_text'):
            await update_or_query.edit_message_text(
                response,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update_or_query.message.reply_text(
                response,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        
    except Exception as e:
        logger.error(f"Ошибка при показе основного списка встреч: {e}")
        error_text = "❌ Произошла ошибка при получении списка встреч."
        
        if hasattr(update_or_query, 'edit_message_text'):
            await update_or_query.edit_message_text(error_text)
        else:
            await update_or_query.message.reply_text(error_text)
