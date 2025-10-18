"""Обработчики для регулярных встреч"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from ..constants import (
    RECURRING_WAITING_TITLE, RECURRING_WAITING_DESCRIPTION, RECURRING_WAITING_TIME,
    RECURRING_WAITING_TYPE, RECURRING_WAITING_INTERVAL, RECURRING_WAITING_WEEKDAYS,
    RECURRING_WAITING_END, MAX_TITLE_LENGTH, MAX_DESCRIPTION_LENGTH
)
from ..utils.helpers import parse_datetime, format_reminder_time

logger = logging.getLogger(__name__)


async def add_recurring_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка названия регулярной встречи"""
    user = update.effective_user
    title = update.message.text.strip()
    
    if len(title) > MAX_TITLE_LENGTH:
        await update.message.reply_text(
            f"⚠️ Название слишком длинное. Максимум {MAX_TITLE_LENGTH} символов. "
            f"Попробуйте еще раз:"
        )
        return RECURRING_WAITING_TITLE
    
    context.user_data['recurring_title'] = title
    logger.info(f"Пользователь {user.id} ввел название регулярной встречи: {title}")
    
    await update.message.reply_text(
        f"📝 Название: **{title}**\n\n"
        f"📄 Теперь введите описание встречи (или отправьте '-' чтобы пропустить):",
        parse_mode='Markdown'
    )
    
    return RECURRING_WAITING_DESCRIPTION


async def add_recurring_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка описания регулярной встречи"""
    user = update.effective_user
    description = update.message.text.strip()
    
    if description == '-':
        description = ""
    elif len(description) > MAX_DESCRIPTION_LENGTH:
        await update.message.reply_text(
            f"⚠️ Описание слишком длинное. Максимум {MAX_DESCRIPTION_LENGTH} символов. "
            f"Попробуйте еще раз:"
        )
        return RECURRING_WAITING_DESCRIPTION
    
    context.user_data['recurring_description'] = description
    logger.info(f"Пользователь {user.id} ввел описание регулярной встречи")
    
    title = context.user_data.get('recurring_title', '')
    desc_text = f"📄 Описание: {description}" if description else "📄 Описание: не указано"
    
    # Показываем выбор типа повторения сразу после описания
    keyboard = [
        [InlineKeyboardButton("📅 Ежедневно", callback_data="recur_daily")],
        [InlineKeyboardButton("📅 Еженедельно", callback_data="recur_weekly")],
        [InlineKeyboardButton("📅 Раз в 2 недели", callback_data="recur_biweekly")],
        [InlineKeyboardButton("📅 Ежемесячно", callback_data="recur_monthly")],
        [InlineKeyboardButton("📅 По будням (пн-пт)", callback_data="recur_weekdays")],
        [InlineKeyboardButton("📅 По определенным дням", callback_data="recur_custom_weekdays")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel_recurring")]
    ]
    
    await update.message.reply_text(
        f"📝 Название: **{title}**\n"
        f"{desc_text}\n\n"
        f"🔄 **Выберите тип повторения:**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    
    return RECURRING_WAITING_TYPE


async def add_recurring_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка времени регулярной встречи с проверкой соответствия типу повторения"""
    from ..main import db
    
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
            return RECURRING_WAITING_TIME
        
        # Получаем тип повторения из контекста
        recurrence_type = context.user_data.get('recurring_type')
        
        # Проверяем соответствие времени типу повторения
        import pytz
        user_tz = pytz.timezone(user_timezone)
        local_time = meeting_time.replace(tzinfo=pytz.UTC).astimezone(user_tz)
        weekday = local_time.weekday()  # 0=понедельник, 6=воскресенье
        
        # Проверка для "по будням"
        if recurrence_type == 'weekdays' and weekday >= 5:  # суббота=5, воскресенье=6
            weekday_names = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
            await update.message.reply_text(
                f"⚠️ Встреча типа 'по будням' не может быть назначена на {weekday_names[weekday]}.\n\n"
                f"Выберите время с понедельника по пятницу:"
            )
            return RECURRING_WAITING_TIME
        
        # Проверка для "по определенным дням"
        if recurrence_type == 'custom_weekdays':
            selected_weekdays = context.user_data.get('recurring_weekdays', '')
            if selected_weekdays:
                allowed_days = [int(d) for d in selected_weekdays.split(',')]
                if weekday not in allowed_days:
                    weekday_names = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
                    allowed_names = [weekday_names[d] for d in allowed_days]
                    await update.message.reply_text(
                        f"⚠️ Встреча назначена на {weekday_names[weekday]}, но выбранные дни повторения: {', '.join(allowed_names)}.\n\n"
                        f"Выберите время в один из выбранных дней:"
                    )
                    return RECURRING_WAITING_TIME
        
        context.user_data['recurring_time'] = meeting_time
        logger.info(f"Пользователь {user.id} ввел время регулярной встречи: {meeting_time}")
        
        # Время прошло все проверки, создаем встречу
        return await create_recurring_meeting(update, context)
        
    except ValueError as e:
        await update.message.reply_text(
            f"⚠️ Неверный формат времени: {str(e)}\n\n"
            f"Попробуйте еще раз. Примеры:\n"
            f"• `14:30` - сегодня в 14:30\n"
            f"• `завтра 10:00` - завтра в 10:00\n"
            f"• `25.12 15:00` - 25 декабря в 15:00"
        )
        return RECURRING_WAITING_TIME


async def add_recurring_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора типа повторения"""
    from ..main import db
    
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    # Парсим тип повторения из callback_data
    if query.data == "recur_custom_weekdays":
        recurrence_type = "custom_weekdays"
    else:
        recurrence_type = query.data.split("_")[1]  # recur_daily -> daily
    
    context.user_data['recurring_type'] = recurrence_type
    logger.info(f"Пользователь {user.id} выбрал тип повторения: {recurrence_type}")
    
    # Если выбран тип "по определенным дням", показываем выбор дней
    if recurrence_type == "custom_weekdays":
        keyboard = [
            [InlineKeyboardButton("Понедельник", callback_data="weekday_0")],
            [InlineKeyboardButton("Вторник", callback_data="weekday_1")],
            [InlineKeyboardButton("Среда", callback_data="weekday_2")],
            [InlineKeyboardButton("Четверг", callback_data="weekday_3")],
            [InlineKeyboardButton("Пятница", callback_data="weekday_4")],
            [InlineKeyboardButton("Суббота", callback_data="weekday_5")],
            [InlineKeyboardButton("Воскресенье", callback_data="weekday_6")],
            [InlineKeyboardButton("✅ Готово", callback_data="weekdays_done")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_recurring")]
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
        
        return RECURRING_WAITING_WEEKDAYS
    else:
        # Для других типов повторения запрашиваем время
        type_names = {
            'daily': 'ежедневно',
            'weekly': 'еженедельно', 
            'biweekly': 'раз в 2 недели',
            'monthly': 'ежемесячно',
            'weekdays': 'по будням (пн-пт)'
        }
        type_display = type_names.get(recurrence_type, recurrence_type)
        
        await query.edit_message_text(
            f"🔄 **Тип повторения:** {type_display}\n\n"
            f"🕐 Теперь введите время первой встречи:\n\n"
            f"Примеры:\n"
            f"• `14:30` - сегодня в 14:30\n"
            f"• `завтра 10:00` - завтра в 10:00\n"
            f"• `25.12 15:00` - 25 декабря в 15:00\n"
            f"• `25.12.2024 15:00` - полная дата",
            parse_mode='Markdown'
        )
        
        return RECURRING_WAITING_TIME


async def add_recurring_weekdays(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора дней недели для регулярной встречи"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "weekdays_done":
        # Завершение выбора дней недели
        selected_weekdays = context.user_data.get('selected_weekdays', [])
        if not selected_weekdays:
            await query.edit_message_text(
                "❌ Выберите хотя бы один день недели!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Назад к выбору дней", callback_data="back_to_weekdays")
                ]])
            )
            return RECURRING_WAITING_WEEKDAYS
        
        # Сохраняем выбранные дни
        weekdays_str = ",".join(map(str, sorted(selected_weekdays)))
        context.user_data['recurring_weekdays'] = weekdays_str
        
        # Показываем выбранные дни и запрашиваем время
        weekday_names = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
        selected_names = [weekday_names[int(d)] for d in weekdays_str.split(',')]
        
        await query.edit_message_text(
            f"🔄 **Тип повторения:** по определенным дням ({', '.join(selected_names)})\n\n"
            f"🕐 Теперь введите время первой встречи:\n\n"
            f"Примеры:\n"
            f"• `14:30` - сегодня в 14:30\n"
            f"• `завтра 10:00` - завтра в 10:00\n"
            f"• `25.12 15:00` - 25 декабря в 15:00\n"
            f"• `25.12.2024 15:00` - полная дата",
            parse_mode='Markdown'
        )
        
        return RECURRING_WAITING_TIME
    
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
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel_recurring")]
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
    
    return RECURRING_WAITING_WEEKDAYS


async def create_recurring_meeting(update, context):
    """Создание регулярной встречи"""
    from ..main import db
    
    user = update.effective_user
    
    # Получаем данные из контекста
    title = context.user_data.get('recurring_title')
    description = context.user_data.get('recurring_description', '')
    meeting_time = context.user_data.get('recurring_time')
    recurrence_type = context.user_data.get('recurring_type')
    weekdays = context.user_data.get('recurring_weekdays', '')
    
    # Создаем встречу в базе данных
    meeting_id = db.add_meeting(
        user_id=user.id,
        title=title,
        description=description,
        meeting_time=meeting_time,
        is_recurring=True,
        recurrence_type=recurrence_type,
        recurrence_weekdays=weekdays
    )
    
    if meeting_id:
        # Получаем настройки напоминания пользователя
        user_reminder_minutes = db.get_user_reminder_minutes(user.id)
        reminder_text = format_reminder_time(user_reminder_minutes)
        
        # Форматируем время для отображения
        user_timezone = db.get_user_timezone(user.id)
        from ..utils.helpers import format_meeting_time_for_user
        time_display = format_meeting_time_for_user(meeting_time, user_timezone)
        
        # Форматируем тип повторения
        type_names = {
            'daily': 'ежедневно',
            'weekly': 'еженедельно',
            'biweekly': 'раз в 2 недели',
            'monthly': 'ежемесячно',
            'weekdays': 'по будням (пн-пт)',
            'custom_weekdays': 'по определенным дням'
        }
        type_display = type_names.get(recurrence_type, recurrence_type)
        
        if recurrence_type == 'custom_weekdays' and weekdays:
            weekday_names = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
            selected_days = [weekday_names[int(d)] for d in weekdays.split(',')]
            type_display += f" ({', '.join(selected_days)})"
        
        success_text = (
            f"✅ **Регулярная встреча создана!**\n\n"
            f"📝 **Название:** {title}\n"
        )
        
        if description:
            success_text += f"📄 **Описание:** {description}\n"
        
        success_text += (
            f"🕐 **Время:** {time_display}\n"
            f"🔄 **Повторение:** {type_display}\n"
            f"🔔 **Напоминание:** за {reminder_text} до начала!"
        )
        
        # Определяем, откуда пришел update - из callback_query или message
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(
                success_text,
                parse_mode='Markdown'
            )
        elif hasattr(update, 'message') and update.message:
            await update.message.reply_text(
                success_text,
                parse_mode='Markdown'
            )
        else:
            # Fallback для случаев, когда update приходит не из стандартных источников
            await update.effective_message.reply_text(
                success_text,
                parse_mode='Markdown'
            )
        
        logger.info(f"Пользователь {user.id} добавил регулярную встречу ID {meeting_id} на {meeting_time}")
    else:
        error_text = "❌ Ошибка при создании встречи. Попробуйте еще раз."
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(error_text)
        elif hasattr(update, 'message') and update.message:
            await update.message.reply_text(error_text)
        else:
            await update.effective_message.reply_text(error_text)
    
    # Очищаем данные пользователя
    context.user_data.clear()
    return ConversationHandler.END


async def add_recurring_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена добавления регулярной встречи"""
    context.user_data.clear()
    
    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text("❌ Добавление регулярной встречи отменено.")
    else:
        await update.message.reply_text("❌ Добавление регулярной встречи отменено.")
    
    return ConversationHandler.END
