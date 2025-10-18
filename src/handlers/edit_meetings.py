"""Обработчики для редактирования встреч"""

import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from ..constants import (
    EDIT_WAITING_CHOICE, EDIT_WAITING_TITLE, EDIT_WAITING_DESCRIPTION, 
    EDIT_WAITING_TIME, EDIT_WAITING_RECURRENCE, EDIT_WAITING_END_DATE, EDIT_WAITING_WEEKDAYS,
    MAX_TITLE_LENGTH, MAX_DESCRIPTION_LENGTH
)
from ..utils.helpers import parse_datetime, format_reminder_time, format_recurrence_info, format_meeting_time_for_user

logger = logging.getLogger(__name__)


async def show_edit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, meeting_id: int, user_id: int, force_new_message: bool = False) -> int:
    """Показать меню редактирования встречи"""
    from ..main import db
    
    # Получаем обновленную информацию о встрече
    meeting = db.get_meeting_by_id(meeting_id, user_id)
    if not meeting:
        # Проверяем, есть ли callback_query или обычное сообщение
        if update.callback_query:
            await update.callback_query.edit_message_text("❌ Встреча не найдена.")
        else:
            await update.message.reply_text("❌ Встреча не найдена.")
        context.user_data.clear()
        return ConversationHandler.END
    
    # Форматируем информацию о встрече в часовом поясе пользователя
    meeting_time = datetime.fromisoformat(meeting['meeting_time'])
    user_timezone = db.get_user_timezone(user_id)
    time_str = format_meeting_time_for_user(meeting_time, user_timezone)
    
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
    
    # Отправляем или редактируем сообщение с меню
    # Проверяем, есть ли callback_query (вызов из кнопки) или обычное сообщение
    if update.callback_query and not force_new_message:
        # Редактируем существующее сообщение
        try:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception:
            # Если не удалось отредактировать, отправляем новое сообщение
            await update.callback_query.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
    else:
        # Отправляем новое сообщение
        if update.callback_query:
            await update.callback_query.message.reply_text(
                text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
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
    
    # Форматируем информацию о встрече в часовом поясе пользователя
    meeting_time = datetime.fromisoformat(meeting['meeting_time'])
    user_timezone = db.get_user_timezone(user.id)
    time_str = format_meeting_time_for_user(meeting_time, user_timezone)
    
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
    from ..main import db  # Импорт здесь для избежания циклических импортов
    
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
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
        # Получаем информацию о встрече
        meeting_id = context.user_data.get('editing_meeting_id')
        meeting = db.get_meeting_by_id(meeting_id, user.id)
        
        if not meeting or not meeting.get('is_recurring'):
            await query.edit_message_text(
                "❌ Эта встреча не является регулярной или не найдена.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="back_to_meetings")]]),
                parse_mode='Markdown'
            )
            return EDIT_WAITING_RECURRENCE
        
        # Создаем кнопки для выбора типа повторения
        from ..constants import RECURRENCE_TYPES, TYPE_NAMES
        keyboard = []
        
        current_type = meeting.get('recurrence_type', 'daily')
        
        for callback_data, recurrence_type in RECURRENCE_TYPES.items():
            type_name = TYPE_NAMES.get(recurrence_type, recurrence_type)
            # Отмечаем текущий тип
            if recurrence_type == current_type:
                type_name = f"✅ {type_name}"
            keyboard.append([InlineKeyboardButton(type_name, callback_data=f"recur_type_{recurrence_type}")])
        
        keyboard.append([InlineKeyboardButton("⬅️ Назад к редактированию", callback_data="back_to_meetings")])
        
        await query.edit_message_text(
            "🔄 **Редактирование повторения**\n\n"
            f"Текущий тип: **{TYPE_NAMES.get(current_type, current_type)}**\n\n"
            "Выберите новый тип повторения:",
            reply_markup=InlineKeyboardMarkup(keyboard),
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
        # Получаем часовой пояс пользователя
        user_timezone = db.get_user_timezone(user.id)
        new_time = parse_datetime(time_str, user_timezone)
        
        # Проверяем, что время в будущем (сравниваем в UTC)
        if new_time <= datetime.utcnow():
            await update.message.reply_text(
                "⚠️ Время встречи должно быть в будущем. Попробуйте еще раз:"
            )
            return EDIT_WAITING_TIME
        
        meeting_id = context.user_data.get('editing_meeting_id')
        if not meeting_id:
            await update.message.reply_text("❌ Ошибка: встреча не найдена.")
            return ConversationHandler.END
        
        # Получаем информацию о встрече для проверки типа повторения
        meeting = db.get_meeting_by_id(meeting_id, user.id)
        if not meeting:
            await update.message.reply_text("❌ Ошибка: встреча не найдена.")
            return ConversationHandler.END
        
        # Проверяем совместимость времени с типом повторения
        if meeting.get('recurrence_type') == 'weekdays':
            # Для встреч "по будням" проверяем, что день недели - рабочий (пн-пт)
            weekday = new_time.weekday()  # 0=понедельник, 6=воскресенье
            if weekday >= 5:  # суббота или воскресенье
                weekday_names = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье']
                current_day = weekday_names[weekday]
                await update.message.reply_text(
                    f"⚠️ Встреча настроена на повторение **по будням (пн-пт)**, "
                    f"но выбранное время приходится на **{current_day}**.\n\n"
                    f"Выберите время в рабочий день (понедельник-пятница) или "
                    f"измените тип повторения встречи.",
                    parse_mode='Markdown'
                )
                return EDIT_WAITING_TIME
        
        # Обновляем встречу
        success = db.update_meeting(meeting_id, user.id, meeting_time=new_time)
        
        if success:
            # Отображаем время в часовом поясе пользователя
            time_display = format_meeting_time_for_user(new_time, user_timezone)
            await update.message.reply_text(f"✅ Время встречи обновлено на: **{time_display}**", parse_mode='Markdown')
            logger.info(f"Пользователь {user.id} обновил время встречи ID {meeting_id} на {new_time}")
            
            # Возвращаемся к меню редактирования встречи
            return await show_edit_menu(update, context, meeting_id, user.id, force_new_message=True)
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


async def edit_recurrence_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора нового типа повторения"""
    from ..main import db
    
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    # Извлекаем новый тип повторения из callback_data
    if query.data == "recur_type_custom_weekdays":
        new_recurrence_type = "custom_weekdays"
    else:
        new_recurrence_type = query.data.split("_")[2]  # recur_type_daily -> daily
    
    meeting_id = context.user_data.get('editing_meeting_id')
    if not meeting_id:
        await query.edit_message_text("❌ Ошибка: встреча не найдена.")
        return ConversationHandler.END
    
    # Если выбран тип "по определенным дням", показываем выбор дней недели
    if new_recurrence_type == "custom_weekdays":
        # Сохраняем выбранный тип в контексте
        context.user_data['new_recurrence_type'] = new_recurrence_type
        
        # Показываем выбор дней недели
        keyboard = [
            [InlineKeyboardButton("Понедельник", callback_data="weekday_0")],
            [InlineKeyboardButton("Вторник", callback_data="weekday_1")],
            [InlineKeyboardButton("Среда", callback_data="weekday_2")],
            [InlineKeyboardButton("Четверг", callback_data="weekday_3")],
            [InlineKeyboardButton("Пятница", callback_data="weekday_4")],
            [InlineKeyboardButton("Суббота", callback_data="weekday_5")],
            [InlineKeyboardButton("Воскресенье", callback_data="weekday_6")],
            [InlineKeyboardButton("✅ Готово", callback_data="weekdays_done")],
            [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_meetings")]
        ]
        
        await query.edit_message_text(
            "📅 **Выберите дни недели для повторения:**\n\n"
            "Нажмите на дни, в которые должна повторяться встреча.\n"
            "Нажмите '✅ Готово' когда закончите выбор.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        # Инициализируем список выбранных дней
        context.user_data['selected_weekdays'] = []
        
        return EDIT_WAITING_WEEKDAYS
    else:
        # Для других типов повторения обновляем сразу
        # Но сначала проверяем, нужно ли скорректировать дату
        meeting = db.get_meeting_by_id(meeting_id, user.id)
        if not meeting:
            await query.edit_message_text("❌ Ошибка: встреча не найдена.")
            return ConversationHandler.END
        
        current_time = datetime.fromisoformat(meeting['meeting_time'])
        new_time = current_time
        time_adjusted = False
        
        # Автоматическая корректировка времени для "по будням"
        if new_recurrence_type == 'weekdays':
            weekday = current_time.weekday()  # 0=понедельник, 6=воскресенье
            if weekday >= 5:  # суббота или воскресенье
                # Переносим на ближайший понедельник
                days_to_add = 7 - weekday  # суббота: 7-5=2, воскресенье: 7-6=1
                new_time = current_time + timedelta(days=days_to_add)
                time_adjusted = True
        
        # Обновляем встречу с новым типом повторения и возможно скорректированным временем
        if time_adjusted:
            success = db.update_meeting(meeting_id, user.id, 
                                      recurrence_type=new_recurrence_type, 
                                      meeting_time=new_time)
        else:
            success = db.update_meeting(meeting_id, user.id, recurrence_type=new_recurrence_type)
        
        if success:
            from ..constants import TYPE_NAMES
            type_name = TYPE_NAMES.get(new_recurrence_type, new_recurrence_type)
            
            message = f"✅ Тип повторения обновлен на: **{type_name}**"
            
            if time_adjusted:
                # Получаем часовой пояс пользователя для отображения
                user_timezone = db.get_user_timezone(user.id)
                time_display = format_meeting_time_for_user(new_time, user_timezone)
                message += f"\n\n⏰ Время автоматически скорректировано на ближайший рабочий день: **{time_display}**"
            
            await query.edit_message_text(message, parse_mode='Markdown')
            logger.info(f"Пользователь {user.id} обновил тип повторения встречи ID {meeting_id} на {new_recurrence_type}")
            if time_adjusted:
                logger.info(f"Время встречи ID {meeting_id} автоматически скорректировано на {new_time}")
            
            # Возвращаемся к меню редактирования встречи
            return await show_edit_menu(update, context, meeting_id, user.id, force_new_message=True)
        else:
            await query.edit_message_text("❌ Ошибка при обновлении типа повторения.")
            context.user_data.clear()
            return ConversationHandler.END


async def edit_weekday_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора дня недели"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "weekdays_done":
        # Завершение выбора дней недели
        return await finalize_weekdays_selection(update, context)
    
    # Извлекаем номер дня недели
    weekday = int(query.data.split("_")[1])
    
    # Получаем текущий список выбранных дней
    selected_weekdays = context.user_data.get('selected_weekdays', [])
    
    # Переключаем выбор дня
    if weekday in selected_weekdays:
        selected_weekdays.remove(weekday)
    else:
        selected_weekdays.append(weekday)
    
    context.user_data['selected_weekdays'] = selected_weekdays
    
    # Обновляем клавиатуру с отмеченными днями
    weekday_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    keyboard = []
    
    for i, name in enumerate(weekday_names):
        if i in selected_weekdays:
            keyboard.append([InlineKeyboardButton(f"✅ {name}", callback_data=f"weekday_{i}")])
        else:
            keyboard.append([InlineKeyboardButton(name, callback_data=f"weekday_{i}")])
    
    keyboard.extend([
        [InlineKeyboardButton("✅ Готово", callback_data="weekdays_done")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_meetings")]
    ])
    
    selected_names = [weekday_names[i] for i in sorted(selected_weekdays)]
    selected_text = ", ".join(selected_names) if selected_names else "не выбраны"
    
    await query.edit_message_text(
        f"📅 **Выберите дни недели для повторения:**\n\n"
        f"**Выбранные дни:** {selected_text}\n\n"
        f"Нажмите на дни, чтобы добавить/убрать их из списка.\n"
        f"Нажмите '✅ Готово' когда закончите выбор.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return EDIT_WAITING_WEEKDAYS


async def finalize_weekdays_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Завершение выбора дней недели и обновление встречи"""
    from ..main import db
    
    query = update.callback_query
    user = update.effective_user
    
    selected_weekdays = context.user_data.get('selected_weekdays', [])
    meeting_id = context.user_data.get('editing_meeting_id')
    new_recurrence_type = context.user_data.get('new_recurrence_type')
    
    if not selected_weekdays:
        await query.edit_message_text(
            "❌ Выберите хотя бы один день недели!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Назад к выбору дней", callback_data="back_to_weekdays")
            ]])
        )
        return EDIT_WAITING_WEEKDAYS
    
    # Преобразуем список дней в строку для сохранения
    weekdays_str = ",".join(map(str, sorted(selected_weekdays)))
    
    # Логируем выбранные дни для отладки
    weekday_names = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    selected_names = [weekday_names[d] for d in selected_weekdays]
    logger.info(f"Выбраны дни недели: {selected_names} (индексы: {selected_weekdays})")
    
    # Проверяем, нужно ли скорректировать дату
    meeting = db.get_meeting_by_id(meeting_id, user.id)
    if not meeting:
        await query.edit_message_text("❌ Ошибка: встреча не найдена.")
        return ConversationHandler.END
    
    current_time = datetime.fromisoformat(meeting['meeting_time'])
    current_weekday = current_time.weekday()  # 0=понедельник, 6=воскресенье
    new_time = current_time
    time_adjusted = False
    
    # Проверяем, нужна ли корректировка даты
    # 1. Если текущий день недели не входит в выбранные дни
    # 2. Если встреча уже в прошлом (для регулярных встреч)
    needs_adjustment = (current_weekday not in selected_weekdays) or (current_time <= datetime.utcnow())
    
    if needs_adjustment:
        # Ищем ближайший день из выбранных
        days_ahead = []
        
        # Если встреча в прошлом, ищем от сегодняшнего дня
        if current_time <= datetime.utcnow():
            today_weekday = datetime.utcnow().weekday()
            for selected_day in selected_weekdays:
                if selected_day >= today_weekday:
                    # День на этой неделе (сегодня или позже)
                    days_ahead.append(selected_day - today_weekday)
                else:
                    # День на следующей неделе
                    days_ahead.append(7 - today_weekday + selected_day)
            
            # Корректируем от сегодняшней даты
            today = datetime.utcnow().replace(hour=current_time.hour, minute=current_time.minute, second=0, microsecond=0)
            if days_ahead:
                min_days = min(days_ahead)
                new_time = today + timedelta(days=min_days)
                time_adjusted = True
        else:
            # Встреча в будущем, корректируем от текущей даты встречи
            for selected_day in selected_weekdays:
                if selected_day > current_weekday:
                    # День на этой неделе
                    days_ahead.append(selected_day - current_weekday)
                else:
                    # День на следующей неделе
                    days_ahead.append(7 - current_weekday + selected_day)
            
            if days_ahead:
                min_days = min(days_ahead)
                new_time = current_time + timedelta(days=min_days)
                time_adjusted = True
        
        # Логируем для отладки
        if time_adjusted:
            weekday_names = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
            current_day_name = weekday_names[current_weekday]
            selected_names = [weekday_names[d] for d in selected_weekdays]
            logger.info(f"Корректировка даты: с {current_day_name} на {', '.join(selected_names)}, новое время: {new_time}")
    
    # Обновляем встречу с новым типом повторения, днями недели и возможно скорректированным временем
    if time_adjusted:
        success = db.update_meeting(
            meeting_id, 
            user.id, 
            recurrence_type=new_recurrence_type,
            recurrence_weekdays=weekdays_str,
            meeting_time=new_time
        )
    else:
        success = db.update_meeting(
            meeting_id, 
            user.id, 
            recurrence_type=new_recurrence_type,
            recurrence_weekdays=weekdays_str
        )
    
    if success:
        weekday_names = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
        selected_names = [weekday_names[i] for i in sorted(selected_weekdays)]
        days_text = ", ".join(selected_names)
        
        message = f"✅ Тип повторения обновлен на: **по определенным дням ({days_text})**"
        
        if time_adjusted:
            # Получаем часовой пояс пользователя для отображения
            user_timezone = db.get_user_timezone(user.id)
            time_display = format_meeting_time_for_user(new_time, user_timezone)
            message += f"\n\n⏰ Время автоматически скорректировано на ближайший подходящий день: **{time_display}**"
        
        await query.edit_message_text(message, parse_mode='Markdown')
        logger.info(f"Пользователь {user.id} обновил тип повторения встречи ID {meeting_id} на {new_recurrence_type} с днями {weekdays_str}")
        if time_adjusted:
            logger.info(f"Время встречи ID {meeting_id} автоматически скорректировано на {new_time}")
        
        # Очищаем временные данные
        context.user_data.pop('selected_weekdays', None)
        context.user_data.pop('new_recurrence_type', None)
        
        # Возвращаемся к меню редактирования встречи
        return await show_edit_menu(update, context, meeting_id, user.id)
    else:
        await query.edit_message_text("❌ Ошибка при обновлении типа повторения.")
        context.user_data.clear()
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
