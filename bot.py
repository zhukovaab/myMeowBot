import os
import logging
import requests
import signal
import sys
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, ConversationHandler, MessageHandler, filters
from telegram.error import TimedOut, NetworkError, RetryAfter
from database import MeetingDatabase
from reminder_system import ReminderSystem

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

# Глобальные переменные
shutdown_requested = False
db = None
reminder_system = None

# Состояния для ConversationHandler
WAITING_TITLE, WAITING_DESCRIPTION, WAITING_TIME = range(3)
EDIT_WAITING_CHOICE, EDIT_WAITING_TITLE, EDIT_WAITING_DESCRIPTION, EDIT_WAITING_TIME, EDIT_WAITING_RECURRENCE, EDIT_WAITING_END_DATE = range(4, 10)
# Состояния для регулярных встреч
RECURRING_WAITING_TITLE, RECURRING_WAITING_DESCRIPTION, RECURRING_WAITING_TIME, RECURRING_WAITING_TYPE, RECURRING_WAITING_INTERVAL, RECURRING_WAITING_WEEKDAYS, RECURRING_WAITING_END = range(15, 22)
# Состояния для настроек
SETTINGS_WAITING_REMINDER_TIME = 22

def format_reminder_time(minutes: int) -> str:
    """Форматирует время напоминания с правильным склонением"""
    if minutes == 1:
        return "1 минуту"
    elif minutes in [2, 3, 4]:
        return f"{minutes} минуты"
    else:
        return f"{minutes} минут"

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

**Основные:**
/start - Начать работу с ботом
/meow - Получить случайную картинку кошки
/help - Показать это сообщение

**Встречи:**
/add_meeting - Добавить новую встречу
/add_recurring - Добавить регулярную встречу
/meetings - Показать список встреч
/edit_meeting - Редактировать встречу
/delete_meeting - Удалить встречу

**Настройки:**
/settings - Настройки напоминаний

**Особенности:**
🔔 Настраиваемое время напоминаний (по умолчанию за 2 минуты)
🗑️ Автоматическое удаление прошедших встреч
🔄 Поддержка регулярных встреч (ежедневно, еженедельно, ежемесячно)
        """
        await update.message.reply_text(help_text)
    except (TimedOut, NetworkError) as e:
        logger.error(f"Ошибка сети при отправке help: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка в help: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Исключение при обработке обновления {update}: {context.error}")

# ============= ФУНКЦИИ ДЛЯ РАБОТЫ С ВСТРЕЧАМИ =============

def parse_datetime(date_str: str) -> datetime:
    """Парсинг строки с датой и временем"""
    # Убираем лишние пробелы
    date_str = date_str.strip()
    
    # Паттерны для разных форматов
    patterns = [
        # ДД.ММ.ГГГГ ЧЧ:ММ (с двузначными минутами)
        (r'^(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{1,2}):(\d{2})$', '%d.%m.%Y %H:%M'),
        # ДД.ММ.ГГГГ ЧЧ:М (с однозначными минутами)
        (r'^(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{1,2}):(\d{1})$', '%d.%m.%Y %H:%M'),
        # ДД.ММ ЧЧ:ММ (текущий год, двузначные минуты)
        (r'^(\d{1,2})\.(\d{1,2})\s+(\d{1,2}):(\d{2})$', '%d.%m %H:%M'),
        # ДД.ММ ЧЧ:М (текущий год, однозначные минуты)
        (r'^(\d{1,2})\.(\d{1,2})\s+(\d{1,2}):(\d{1})$', '%d.%m %H:%M'),
        # ЧЧ:ММ (сегодня, двузначные минуты)
        (r'^(\d{1,2}):(\d{2})$', '%H:%M'),
        # ЧЧ:М (сегодня, однозначные минуты)
        (r'^(\d{1,2}):(\d{1})$', '%H:%M'),
        # завтра ЧЧ:ММ (двузначные минуты)
        (r'^завтра\s+(\d{1,2}):(\d{2})$', 'tomorrow %H:%M'),
        # завтра ЧЧ:М (однозначные минуты)
        (r'^завтра\s+(\d{1,2}):(\d{1})$', 'tomorrow %H:%M'),
    ]
    
    for pattern, fmt in patterns:
        match = re.match(pattern, date_str, re.IGNORECASE)
        if match:
            try:
                if fmt == 'tomorrow %H:%M':
                    # Завтра
                    hour, minute = map(int, match.groups())
                    tomorrow = datetime.now() + timedelta(days=1)
                    return tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
                elif fmt == '%H:%M':
                    # Сегодня
                    hour, minute = map(int, match.groups())
                    today = datetime.now()
                    result = today.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    # Если время уже прошло сегодня, переносим на завтра
                    if result <= today:
                        result += timedelta(days=1)
                    return result
                elif fmt == '%d.%m %H:%M':
                    # Текущий год
                    day, month, hour, minute = map(int, match.groups())
                    year = datetime.now().year
                    return datetime(year, month, day, hour, minute)
                else:
                    # Полная дата
                    return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
    
    raise ValueError("Неверный формат даты и времени")

async def add_meeting_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало добавления встречи"""
    user = update.effective_user
    logger.info(f"Пользователь {user.id} начал добавление встречи")
    
    await update.message.reply_text(
        "📝 Добавление новой встречи\n\n"
        "Введите название встречи:"
    )
    return WAITING_TITLE

async def add_meeting_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение названия встречи"""
    title = update.message.text.strip()
    if not title:
        await update.message.reply_text("Название не может быть пустым. Попробуйте еще раз:")
        return WAITING_TITLE
    
    context.user_data['meeting_title'] = title
    await update.message.reply_text(
        "📄 Введите описание встречи (или отправьте '-' чтобы пропустить):"
    )
    return WAITING_DESCRIPTION

async def add_meeting_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение описания встречи"""
    description = update.message.text.strip()
    if description == '-':
        description = ""
    
    context.user_data['meeting_description'] = description
    await update.message.reply_text(
        "🕐 Введите дату и время встречи в одном из форматов:\n\n"
        "• `15:30` или `2:30` - сегодня в указанное время (если не прошло) или завтра\n"
        "• `завтра 10:00` - завтра в 10:00\n"
        "• `25.12 14:00` - 25 декабря в 14:00\n"
        "• `25.12.2024 14:00` - 25 декабря 2024 года в 14:00",
        parse_mode='Markdown'
    )
    return WAITING_TIME

async def add_meeting_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение времени встречи и сохранение"""
    user = update.effective_user
    time_str = update.message.text.strip()
    
    try:
        meeting_time = parse_datetime(time_str)
        
        # Проверяем, что время в будущем
        if meeting_time <= datetime.now():
            await update.message.reply_text(
                "⚠️ Время встречи должно быть в будущем. Попробуйте еще раз:"
            )
            return WAITING_TIME
        
        # Сохраняем встречу
        title = context.user_data['meeting_title']
        description = context.user_data['meeting_description']
        
        meeting_id = db.add_meeting(user.id, title, description, meeting_time)
        
        # Форматируем время для отображения
        time_display = meeting_time.strftime("%d.%m.%Y в %H:%M")
        
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
        
        logger.info(f"Пользователь {user.id} добавил встречу '{title}' на {meeting_time}")
        return ConversationHandler.END
        
    except ValueError as e:
        await update.message.reply_text(
            f"⚠️ Ошибка в формате времени: {str(e)}\n\n"
            "Попробуйте еще раз в одном из форматов:\n"
            "• `15:30` или `2:30`\n"
            "• `завтра 10:00`\n"
            "• `25.12 14:00`\n"
            "• `25.12.2024 14:00`",
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
    user = update.effective_user
    logger.info(f"Пользователь {user.id} запросил список встреч")
    
    try:
        meetings = db.get_user_meetings(user.id)
        
        if not meetings:
            await update.message.reply_text(
                "📅 У вас пока нет запланированных встреч.\n\n"
                "Используйте /add_meeting чтобы добавить новую встречу."
            )
            return
        
        # Разделяем встречи на прошедшие и предстоящие
        now = datetime.now()
        upcoming = []
        past = []
        
        for meeting in meetings:
            meeting_time = datetime.fromisoformat(meeting['meeting_time'])
            if meeting_time > now:
                upcoming.append((meeting, meeting_time))
            else:
                past.append((meeting, meeting_time))
        
        response = "📅 **Ваши встречи:**\n\n"
        
        # Предстоящие встречи
        if upcoming:
            response += "🔜 **Предстоящие:**\n"
            for meeting, meeting_time in upcoming:
                time_str = meeting_time.strftime("%d.%m.%Y в %H:%M")
                
                # Иконка для регулярных встреч
                icon = "🔄" if meeting.get('is_recurring') else "📅"
                
                response += f"• `{meeting['id']}` {icon} {meeting['title']}\n"
                response += f"  🕐 {time_str}\n"
                
                if meeting['description']:
                    response += f"  📄 {meeting['description']}\n"
                
                # Информация о регулярности
                if meeting.get('is_recurring'):
                    recurrence_type = meeting.get('recurrence_type', '')
                    interval = meeting.get('recurrence_interval', 1)
                    weekdays = meeting.get('recurrence_weekdays')
                    
                    if recurrence_type == 'daily':
                        if interval == 1:
                            recurrence_text = "ежедневно"
                        else:
                            recurrence_text = f"каждые {interval} дня"
                    elif recurrence_type == 'weekly':
                        if interval == 1:
                            recurrence_text = "еженедельно"
                        else:
                            recurrence_text = f"каждые {interval} недели"
                    elif recurrence_type == 'biweekly':
                        if interval == 1:
                            recurrence_text = "раз в 2 недели"
                        else:
                            recurrence_text = f"каждые {2 * interval} недели"
                    elif recurrence_type == 'monthly':
                        if interval == 1:
                            recurrence_text = "ежемесячно"
                        else:
                            recurrence_text = f"каждые {interval} месяца"
                    elif recurrence_type == 'weekdays':
                        recurrence_text = "по будням (пн-пт)"
                    elif recurrence_type == 'custom_weekdays' and weekdays:
                        weekday_names = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']
                        try:
                            selected_days = [weekday_names[int(d)] for d in weekdays.split(',')]
                            recurrence_text = f"по {', '.join(selected_days)}"
                        except (ValueError, IndexError):
                            recurrence_text = "по выбранным дням"
                    else:
                        recurrence_text = "регулярно"
                    
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
                time_str = meeting_time.strftime("%d.%m.%Y в %H:%M")
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

async def edit_meeting_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало редактирования встречи"""
    user = update.effective_user
    logger.info(f"Пользователь {user.id} начал редактирование встречи")
    
    # Получаем ID встречи из аргументов команды
    args = context.args
    if args:
        try:
            meeting_id = int(args[0])
            meeting = db.get_meeting_by_id(meeting_id, user.id)
            
            if not meeting:
                await update.message.reply_text(
                    f"❌ Встреча с ID {meeting_id} не найдена или не принадлежит вам."
                )
                return ConversationHandler.END
            
            context.user_data['edit_meeting_id'] = meeting_id
            context.user_data['edit_meeting'] = meeting
            
            # Показываем текущую информацию и варианты редактирования
            meeting_time = datetime.fromisoformat(meeting['meeting_time'])
            time_str = meeting_time.strftime("%d.%m.%Y в %H:%M")
            
            keyboard = [
                [InlineKeyboardButton("📝 Название", callback_data="edit_title")],
                [InlineKeyboardButton("📄 Описание", callback_data="edit_description")],
                [InlineKeyboardButton("🕐 Время", callback_data="edit_time")],
                [InlineKeyboardButton("📋 К списку встреч", callback_data="back_to_meetings")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✏️ **Редактирование встречи ID {meeting_id}**\n\n"
                f"📝 Название: {meeting['title']}\n"
                f"📄 Описание: {meeting['description'] if meeting['description'] else 'Не указано'}\n"
                f"🕐 Время: {time_str}\n\n"
                f"Что хотите изменить?",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return EDIT_WAITING_CHOICE
            
        except ValueError:
            pass
    
    # Если ID не указан, просим ввести
    await update.message.reply_text(
        "✏️ Редактирование встречи\n\n"
        "Введите ID встречи для редактирования:\n"
        "(ID можно узнать командой /meetings)"
    )
    return EDIT_WAITING_CHOICE

async def edit_meeting_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора что редактировать"""
    query = update.callback_query
    await query.answer()
    
    choice = query.data
    
    # Обработка новых callback данных с ID встречи
    if "_" in choice and choice.count("_") >= 2:
        parts = choice.split("_")
        action = parts[1]  # title, description, time, cancel
        meeting_id = int(parts[2])
        
        if action == "cancel":
            context.user_data.clear()
            await query.edit_message_text("❌ Редактирование отменено.")
            return ConversationHandler.END
        
        # Получаем встречу по ID
        user = update.effective_user
        meeting = db.get_meeting_by_id(meeting_id, user.id)
        if not meeting:
            await query.edit_message_text("❌ Встреча не найдена.")
            return ConversationHandler.END
        
        context.user_data['edit_meeting_id'] = meeting_id
        context.user_data['edit_meeting'] = meeting
        
        if action == "title":
            await query.edit_message_text(
                f"📝 Текущее название: {meeting['title']}\n\n"
                f"Введите новое название:"
            )
            return EDIT_WAITING_TITLE
        
        elif action == "description":
            current_desc = meeting['description'] if meeting['description'] else 'Не указано'
            await query.edit_message_text(
                f"📄 Текущее описание: {current_desc}\n\n"
                f"Введите новое описание (или '-' чтобы убрать):"
            )
            return EDIT_WAITING_DESCRIPTION
        
        elif action == "time":
            meeting_time = datetime.fromisoformat(meeting['meeting_time'])
            time_str = meeting_time.strftime("%d.%m.%Y в %H:%M")
            await query.edit_message_text(
                f"🕐 Текущее время: {time_str}\n\n"
                f"Введите новое время в формате:\n"
                f"• `15:30` или `2:30`\n"
                f"• `завтра 10:00`\n"
                f"• `25.12 14:00`\n"
                f"• `25.12.2024 14:00`",
                parse_mode='Markdown'
            )
            return EDIT_WAITING_TIME
        
        elif action == "recurrence":
            # Показываем текущий режим повторения и предлагаем изменить
            recurrence_info = ""
            if meeting.get('recurrence_type'):
                recurrence_type = meeting['recurrence_type']
                interval = meeting.get('recurrence_interval', 1)
                weekdays = meeting.get('recurrence_weekdays')
                
                if recurrence_type == 'daily':
                    recurrence_info = f"Ежедневно (каждые {interval} дн.)" if interval > 1 else "Ежедневно"
                elif recurrence_type == 'weekly':
                    recurrence_info = f"Еженедельно (каждые {interval} нед.)" if interval > 1 else "Еженедельно"
                elif recurrence_type == 'biweekly':
                    recurrence_info = "Раз в 2 недели"
                elif recurrence_type == 'monthly':
                    recurrence_info = f"Ежемесячно (каждые {interval} мес.)" if interval > 1 else "Ежемесячно"
                elif recurrence_type == 'weekdays':
                    recurrence_info = "По будням (пн-пт)"
                elif recurrence_type == 'custom_weekdays' and weekdays:
                    days_map = {'0': 'пн', '1': 'вт', '2': 'ср', '3': 'чт', '4': 'пт', '5': 'сб', '6': 'вс'}
                    selected_days = [days_map.get(d, d) for d in weekdays.split(',')]
                    recurrence_info = f"По дням: {', '.join(selected_days)}"
            
            keyboard = [
                [InlineKeyboardButton("📅 Ежедневно", callback_data="recur_daily")],
                [InlineKeyboardButton("📅 Еженедельно", callback_data="recur_weekly")],
                [InlineKeyboardButton("📅 Раз в 2 недели", callback_data="recur_biweekly")],
                [InlineKeyboardButton("📅 Ежемесячно", callback_data="recur_monthly")],
                [InlineKeyboardButton("💼 По будням", callback_data="recur_weekdays")],
                [InlineKeyboardButton("📋 По определенным дням", callback_data="recur_custom")],
                [InlineKeyboardButton("⬅️ Назад к редактированию", callback_data=f"edit_{meeting_id}")]
            ]
            
            await query.edit_message_text(
                f"🔄 Текущий режим: {recurrence_info}\n\n"
                f"Выберите новый режим повторения:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return EDIT_WAITING_RECURRENCE
        
        elif action == "enddate":  # edit_enddate_ID
            # Для callback edit_enddate_ID: parts = ["edit", "enddate", "ID"]
            meeting_id = int(parts[2])
            
            # Получаем встречу по ID
            user = update.effective_user
            meeting = db.get_meeting_by_id(meeting_id, user.id)
            if not meeting:
                await query.edit_message_text("❌ Встреча не найдена.")
                return ConversationHandler.END
            
            context.user_data['edit_meeting_id'] = meeting_id
            context.user_data['edit_meeting'] = meeting
            
            current_end = meeting.get('recurrence_end_date')
            if current_end:
                end_date = datetime.fromisoformat(current_end)
                end_str = end_date.strftime("%d.%m.%Y")
            else:
                end_str = "Не установлена"
            
            await query.edit_message_text(
                f"📅 Текущая дата окончания: {end_str}\n\n"
                f"Введите новую дату окончания в формате:\n"
                f"• `25.12` - 25 декабря этого года\n"
                f"• `25.12.2024` - 25 декабря 2024 года\n"
                f"• `-` - убрать дату окончания (бесконечное повторение)",
                parse_mode='Markdown'
            )
            return EDIT_WAITING_END_DATE
    
    # Старая логика для обратной совместимости
    if choice == "back_to_meetings":
        context.user_data.clear()
        await show_main_meetings_list(query, user.id)
        return ConversationHandler.END
    
    meeting = context.user_data.get('edit_meeting')
    if not meeting:
        await query.edit_message_text("❌ Данные встречи не найдены.")
        return ConversationHandler.END
    
    if choice == "edit_title":
        await query.edit_message_text(
            f"📝 Текущее название: {meeting['title']}\n\n"
            f"Введите новое название:"
        )
        return EDIT_WAITING_TITLE
    
    elif choice == "edit_description":
        current_desc = meeting['description'] if meeting['description'] else 'Не указано'
        await query.edit_message_text(
            f"📄 Текущее описание: {current_desc}\n\n"
            f"Введите новое описание (или '-' чтобы убрать):"
        )
        return EDIT_WAITING_DESCRIPTION
    
    elif choice == "edit_time":
        meeting_time = datetime.fromisoformat(meeting['meeting_time'])
        time_str = meeting_time.strftime("%d.%m.%Y в %H:%M")
        await query.edit_message_text(
            f"🕐 Текущее время: {time_str}\n\n"
            f"Введите новое время в формате:\n"
            f"• `15:30` или `2:30`\n"
            f"• `завтра 10:00`\n"
            f"• `25.12 14:00`\n"
            f"• `25.12.2024 14:00`",
            parse_mode='Markdown'
        )
        return EDIT_WAITING_TIME

async def edit_meeting_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обновление названия встречи"""
    user = update.effective_user
    new_title = update.message.text.strip()
    
    if not new_title:
        await update.message.reply_text("Название не может быть пустым. Попробуйте еще раз:")
        return EDIT_WAITING_TITLE
    
    meeting_id = context.user_data['edit_meeting_id']
    
    if db.update_meeting(meeting_id, user.id, title=new_title):
        await show_meeting_info_after_edit(update, meeting_id, user.id, f"📝 Название обновлено на: {new_title}")
        context.user_data.clear()
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ Ошибка при обновлении встречи.")
        return ConversationHandler.END

async def edit_meeting_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обновление описания встречи"""
    user = update.effective_user
    new_description = update.message.text.strip()
    
    if new_description == '-':
        new_description = ""
    
    meeting_id = context.user_data['edit_meeting_id']
    
    if db.update_meeting(meeting_id, user.id, description=new_description):
        desc_text = new_description if new_description else "убрано"
        await show_meeting_info_after_edit(update, meeting_id, user.id, f"📄 Описание обновлено: {desc_text}")
        context.user_data.clear()
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ Ошибка при обновлении встречи.")
        return ConversationHandler.END

async def edit_meeting_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обновление времени встречи"""
    user = update.effective_user
    time_str = update.message.text.strip()
    
    try:
        new_time = parse_datetime(time_str)
        
        if new_time <= datetime.now():
            await update.message.reply_text(
                "⚠️ Время встречи должно быть в будущем. Попробуйте еще раз:"
            )
            return EDIT_WAITING_TIME
        
        meeting_id = context.user_data['edit_meeting_id']
        
        if db.update_meeting(meeting_id, user.id, meeting_time=new_time):
            time_display = new_time.strftime("%d.%m.%Y в %H:%M")
            await show_meeting_info_after_edit(update, meeting_id, user.id, f"🕐 Время обновлено на: {time_display}")
            context.user_data.clear()
            return ConversationHandler.END
        else:
            await update.message.reply_text("❌ Ошибка при обновлении встречи.")
            return ConversationHandler.END
            
    except ValueError as e:
        await update.message.reply_text(
            f"⚠️ Ошибка в формате времени: {str(e)}\n\n"
            "Попробуйте еще раз."
        )
        return EDIT_WAITING_TIME

async def edit_meeting_recurrence(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка изменения режима повторения"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    meeting_id = context.user_data.get('edit_meeting_id')
    
    if not meeting_id:
        await query.edit_message_text("❌ Ошибка: данные встречи не найдены.")
        return ConversationHandler.END
    
    recurrence_type = query.data.split("_")[1]  # daily, weekly, etc.
    
    if recurrence_type == "cancel":
        await query.edit_message_text("❌ Изменение режима повторения отменено.")
        return ConversationHandler.END
    
    try:
        # Определяем параметры повторения
        recurrence_params = {
            'is_recurring': True,
            'recurrence_type': recurrence_type,
            'recurrence_interval': 1,
            'recurrence_weekdays': None
        }
        
        if recurrence_type == 'custom':
            # Для кастомных дней недели показываем выбор
            keyboard = [
                [InlineKeyboardButton("Пн", callback_data="wd_0"), InlineKeyboardButton("Вт", callback_data="wd_1"), InlineKeyboardButton("Ср", callback_data="wd_2")],
                [InlineKeyboardButton("Чт", callback_data="wd_3"), InlineKeyboardButton("Пт", callback_data="wd_4")],
                [InlineKeyboardButton("Сб", callback_data="wd_5"), InlineKeyboardButton("Вс", callback_data="wd_6")],
                [InlineKeyboardButton("✅ Готово", callback_data="recur_custom_done"), InlineKeyboardButton("⬅️ Назад", callback_data=f"edit_recurrence_{meeting_id}")]
            ]
            
            context.user_data['selected_weekdays'] = []
            await query.edit_message_text(
                "📋 Выберите дни недели для повторения:\n\n"
                "Нажмите на дни, которые хотите выбрать, затем нажмите ✅ Готово",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return EDIT_WAITING_RECURRENCE
        
        # Обновляем встречу
        success = db.update_meeting(
            meeting_id=meeting_id,
            user_id=user.id,
            **recurrence_params
        )
        
        if success:
            # Показываем обновленную информацию о встрече
            await show_meeting_info_after_edit(query, meeting_id, user.id, "🔄 Режим повторения успешно изменен!")
        else:
            await query.edit_message_text("❌ Ошибка при изменении режима повторения.")
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Ошибка при изменении режима повторения: {e}")
        await query.edit_message_text("❌ Произошла ошибка при изменении режима повторения.")
        return ConversationHandler.END

async def edit_meeting_end_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка изменения даты окончания"""
    user = update.effective_user
    meeting_id = context.user_data.get('edit_meeting_id')
    new_end_date_str = update.message.text.strip()
    
    if not meeting_id:
        await update.message.reply_text("❌ Ошибка: данные встречи не найдены.")
        return ConversationHandler.END
    
    try:
        end_date = None
        
        if new_end_date_str != '-':
            # Парсим дату окончания
            if '.' in new_end_date_str:
                parts = new_end_date_str.split('.')
                if len(parts) == 2:  # DD.MM
                    day, month = int(parts[0]), int(parts[1])
                    year = datetime.now().year
                    end_date = datetime(year, month, day, 23, 59, 59)
                elif len(parts) == 3:  # DD.MM.YYYY
                    day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                    end_date = datetime(year, month, day, 23, 59, 59)
                else:
                    raise ValueError("Неверный формат даты")
            else:
                raise ValueError("Неверный формат даты")
        
        # Обновляем встречу
        success = db.update_meeting(
            meeting_id=meeting_id,
            user_id=user.id,
            recurrence_end_date=end_date
        )
        
        if success:
            # Показываем обновленную информацию о встрече
            await show_meeting_info_after_edit(update, meeting_id, user.id, "📅 Дата окончания успешно изменена!")
        else:
            await update.message.reply_text("❌ Ошибка при изменении даты окончания.")
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат даты. Используйте:\n"
            "• `25.12` - для 25 декабря этого года\n"
            "• `25.12.2024` - для конкретного года\n"
            "• `-` - для отмены даты окончания"
        )
        return EDIT_WAITING_END_DATE
    except Exception as e:
        logger.error(f"Ошибка при изменении даты окончания: {e}")
        await update.message.reply_text("❌ Произошла ошибка при сохранении даты окончания.")
        return ConversationHandler.END

async def show_meeting_info_after_edit(update_or_query, meeting_id: int, user_id: int, success_message: str):
    """Показывает информацию о встрече после редактирования с кнопками действий"""
    try:
        meeting = db.get_meeting_by_id(meeting_id, user_id)
        if not meeting:
            if hasattr(update_or_query, 'edit_message_text'):
                await update_or_query.edit_message_text("❌ Встреча не найдена.")
            else:
                await update_or_query.message.reply_text("❌ Встреча не найдена.")
            return
        
        # Формируем информацию о встрече
        meeting_time = datetime.fromisoformat(meeting['meeting_time'])
        time_str = meeting_time.strftime("%d.%m.%Y в %H:%M")
        
        info_text = f"✅ {success_message}\n\n"
        info_text += f"📝 **Информация о встрече:**\n\n"
        info_text += f"**Название:** {meeting['title']}\n"
        info_text += f"**Описание:** {meeting['description'] if meeting['description'] else 'Не указано'}\n"
        info_text += f"**Время:** {time_str}\n"
        
        # Добавляем информацию о регулярности
        if meeting.get('is_recurring'):
            recurrence_type = meeting.get('recurrence_type')
            interval = meeting.get('recurrence_interval', 1)
            weekdays = meeting.get('recurrence_weekdays')
            end_date = meeting.get('recurrence_end_date')
            
            if recurrence_type == 'daily':
                recur_text = f"Ежедневно (каждые {interval} дн.)" if interval > 1 else "Ежедневно"
            elif recurrence_type == 'weekly':
                recur_text = f"Еженедельно (каждые {interval} нед.)" if interval > 1 else "Еженедельно"
            elif recurrence_type == 'biweekly':
                recur_text = "Раз в 2 недели"
            elif recurrence_type == 'monthly':
                recur_text = f"Ежемесячно (каждые {interval} мес.)" if interval > 1 else "Ежемесячно"
            elif recurrence_type == 'weekdays':
                recur_text = "По будням (пн-пт)"
            elif recurrence_type == 'custom_weekdays' and weekdays:
                days_map = {'0': 'пн', '1': 'вт', '2': 'ср', '3': 'чт', '4': 'пт', '5': 'сб', '6': 'вс'}
                selected_days = [days_map.get(d, d) for d in weekdays.split(',')]
                recur_text = f"По дням: {', '.join(selected_days)}"
            else:
                recur_text = "Регулярная"
            
            info_text += f"**Повторение:** {recur_text}\n"
            
            if end_date:
                end_dt = datetime.fromisoformat(end_date)
                end_str = end_dt.strftime("%d.%m.%Y")
                info_text += f"**До:** {end_str}\n"
        
        # Кнопки для дальнейших действий
        keyboard = [
            [InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_{meeting_id}")],
            [InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_confirm_{meeting_id}")],
            [InlineKeyboardButton("📋 К списку встреч", callback_data="back_to_meetings")]
        ]
        
        if hasattr(update_or_query, 'edit_message_text'):
            await update_or_query.edit_message_text(
                info_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update_or_query.message.reply_text(
                info_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Ошибка при показе информации о встрече: {e}")
        error_text = "❌ Произошла ошибка при получении информации о встрече."
        if hasattr(update_or_query, 'edit_message_text'):
            await update_or_query.edit_message_text(error_text)
        else:
            await update_or_query.message.reply_text(error_text)

async def show_meetings_for_action(query, user_id: int, action: str, title: str):
    """Показывает список встреч для выбранного действия (редактирование/удаление)"""
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
        
        # Сортируем встречи по времени
        now = datetime.now()
        upcoming = []
        
        for meeting in meetings:
            meeting_time = datetime.fromisoformat(meeting['meeting_time'])
            if meeting_time > now:
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
        
        for meeting, meeting_time in upcoming[:10]:  # Показываем максимум 10 встреч
            meeting_id = meeting['id']
            title_short = meeting['title'][:25] + "..." if len(meeting['title']) > 25 else meeting['title']
            time_str = meeting_time.strftime("%d.%m в %H:%M")
            
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
    try:
        meetings = db.get_user_meetings(user_id)
        
        if not meetings:
            response = "📭 У вас пока нет встреч.\n\n"
            response += "Используйте кнопку ниже, чтобы добавить первую встречу!"
        else:
            # Сортируем встречи по времени
            now = datetime.now()
            upcoming = []
            
            for meeting in meetings:
                meeting_time = datetime.fromisoformat(meeting['meeting_time'])
                if meeting_time > now:
                    upcoming.append((meeting, meeting_time))
            
            upcoming.sort(key=lambda x: x[1])
            
            # Разделяем встречи на прошедшие и предстоящие (та же логика, что в list_meetings)
            past = []
            for meeting in meetings:
                meeting_time = datetime.fromisoformat(meeting['meeting_time'])
                if meeting_time <= now:
                    past.append((meeting, meeting_time))
            
            response = "📅 **Ваши встречи:**\n\n"
            
            # Предстоящие встречи
            if upcoming:
                response += "🔜 **Предстоящие:**\n"
                for meeting, meeting_time in upcoming:
                    time_str = meeting_time.strftime("%d.%m.%Y в %H:%M")
                    
                    # Иконка для регулярных встреч
                    icon = "🔄" if meeting.get('is_recurring') else "📅"
                    
                    response += f"• `{meeting['id']}` {icon} {meeting['title']}\n"
                    response += f"  🕐 {time_str}\n"
                    
                    if meeting['description']:
                        response += f"  📄 {meeting['description']}\n"
                    
                    # Информация о регулярности (упрощенная версия)
                    if meeting.get('is_recurring'):
                        recurrence_type = meeting.get('recurrence_type', '')
                        if recurrence_type == 'daily':
                            response += f"  🔄 Ежедневно\n"
                        elif recurrence_type == 'weekly':
                            response += f"  🔄 Еженедельно\n"
                        elif recurrence_type == 'biweekly':
                            response += f"  🔄 Раз в 2 недели\n"
                        elif recurrence_type == 'monthly':
                            response += f"  🔄 Ежемесячно\n"
                        elif recurrence_type == 'weekdays':
                            response += f"  🔄 По будням\n"
                        elif recurrence_type == 'custom_weekdays':
                            response += f"  🔄 По определенным дням\n"
                        else:
                            response += f"  🔄 Регулярно\n"
                    
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

async def delete_meeting(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Удаление встречи"""
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
        time_str = meeting_time.strftime("%d.%m.%Y в %H:%M")
        
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

async def delete_meeting_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка подтверждения удаления встречи"""
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
        # Не возвращаем состояние, так как это не часть ConversationHandler
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
    
    elif query.data.startswith("edit_") and query.data.count("_") == 1:
        # Обрабатываем только простые edit_ callback'и (например, edit_5)
        meeting_id = int(query.data.split("_")[1])
        
        # Получаем информацию о встрече
        meeting = db.get_meeting_by_id(meeting_id, user.id)
        if not meeting:
            await query.edit_message_text("❌ Встреча не найдена.")
            return
        
        # Показываем меню редактирования
        meeting_time = datetime.fromisoformat(meeting['meeting_time'])
        time_str = meeting_time.strftime("%d.%m.%Y в %H:%M")
        
        keyboard = [
            [InlineKeyboardButton("📝 Название", callback_data=f"edit_title_{meeting_id}")],
            [InlineKeyboardButton("📄 Описание", callback_data=f"edit_description_{meeting_id}")],
            [InlineKeyboardButton("🕐 Время", callback_data=f"edit_time_{meeting_id}")],
        ]
        
        # Добавляем кнопки для регулярных встреч
        if meeting.get('is_recurring'):
            keyboard.extend([
                [InlineKeyboardButton("🔄 Режим повторения", callback_data=f"edit_recurrence_{meeting_id}")],
                [InlineKeyboardButton("📅 Дата окончания", callback_data=f"edit_enddate_{meeting_id}")],
            ])
        else:
            # Для обычных встреч можно сделать регулярными
            keyboard.append([InlineKeyboardButton("🔄 Сделать регулярной", callback_data=f"edit_make_recurring_{meeting_id}")])
        
        keyboard.extend([
            [InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_confirm_{meeting_id}")],
            [InlineKeyboardButton("📋 К списку встреч", callback_data="back_to_meetings")]
        ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✏️ **Редактирование встречи**\n\n"
            f"📝 Название: {meeting['title']}\n"
            f"📄 Описание: {meeting['description'] if meeting['description'] else 'Не указано'}\n"
            f"🕐 Время: {time_str}\n\n"
            f"Что хотите изменить?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return

async def add_meeting_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора типа встречи для добавления"""
    query = update.callback_query
    await query.answer()
    
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
    
    elif query.data == "back_to_meetings":
        await show_main_meetings_list(query, user.id)
        return ConversationHandler.END

# ============= ФУНКЦИИ ДЛЯ РЕГУЛЯРНЫХ ВСТРЕЧ =============

async def add_recurring_meeting_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало добавления регулярной встречи"""
    user = update.effective_user
    logger.info(f"Пользователь {user.id} начал добавление регулярной встречи")
    
    await update.message.reply_text(
        "🔄 Добавление регулярной встречи\n\n"
        "Введите название встречи:"
    )
    return RECURRING_WAITING_TITLE

async def add_recurring_meeting_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение названия регулярной встречи"""
    title = update.message.text.strip()
    if not title:
        await update.message.reply_text("Название не может быть пустым. Попробуйте еще раз:")
        return RECURRING_WAITING_TITLE
    
    context.user_data['recurring_title'] = title
    await update.message.reply_text(
        "📄 Введите описание встречи (или отправьте '-' чтобы пропустить):"
    )
    return RECURRING_WAITING_DESCRIPTION

async def add_recurring_meeting_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение описания регулярной встречи"""
    description = update.message.text.strip()
    if description == '-':
        description = ""
    
    context.user_data['recurring_description'] = description
    await update.message.reply_text(
        "🕐 Введите время первой встречи в одном из форматов:\n\n"
        "• `15:30` или `2:30` - сегодня в указанное время (если не прошло) или завтра\n"
        "• `завтра 10:00` - завтра в 10:00\n"
        "• `25.12 14:00` - 25 декабря в 14:00\n"
        "• `25.12.2024 14:00` - 25 декабря 2024 года в 14:00",
        parse_mode='Markdown'
    )
    return RECURRING_WAITING_TIME

async def add_recurring_meeting_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение времени регулярной встречи"""
    time_str = update.message.text.strip()
    
    try:
        meeting_time = parse_datetime(time_str)
        
        if meeting_time <= datetime.now():
            await update.message.reply_text(
                "⚠️ Время встречи должно быть в будущем. Попробуйте еще раз:"
            )
            return RECURRING_WAITING_TIME
        
        context.user_data['recurring_time'] = meeting_time
        
        # Предлагаем выбрать тип повторения
        keyboard = [
            [InlineKeyboardButton("📅 Ежедневно", callback_data="recur_daily")],
            [InlineKeyboardButton("📅 Еженедельно", callback_data="recur_weekly")],
            [InlineKeyboardButton("📅 Раз в 2 недели", callback_data="recur_biweekly")],
            [InlineKeyboardButton("📅 Ежемесячно", callback_data="recur_monthly")],
            [InlineKeyboardButton("💼 По будням (пн-пт)", callback_data="recur_weekdays")],
            [InlineKeyboardButton("🗓️ По определенным дням", callback_data="recur_custom")],
            [InlineKeyboardButton("📋 К списку встреч", callback_data="back_to_meetings")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔄 Выберите тип повторения:",
            reply_markup=reply_markup
        )
        
        return RECURRING_WAITING_TYPE
        
    except ValueError as e:
        await update.message.reply_text(
            f"⚠️ Ошибка в формате времени: {str(e)}\n\n"
            "Попробуйте еще раз в одном из форматов:\n"
            "• `15:30` или `2:30`\n"
            "• `завтра 10:00`\n"
            "• `25.12 14:00`\n"
            "• `25.12.2024 14:00`",
            parse_mode='Markdown'
        )
        return RECURRING_WAITING_TIME

async def add_recurring_meeting_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора типа повторения"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "back_to_meetings":
        context.user_data.clear()
        await show_main_meetings_list(query, user.id)
        return ConversationHandler.END
    
    # Сохраняем тип повторения
    recurrence_types = {
        "recur_daily": "daily",
        "recur_weekly": "weekly", 
        "recur_biweekly": "biweekly",
        "recur_monthly": "monthly",
        "recur_weekdays": "weekdays",
        "recur_custom": "custom_weekdays"
    }
    
    recurrence_type = recurrence_types.get(query.data)
    context.user_data['recurrence_type'] = recurrence_type
    
    type_names = {
        "daily": "ежедневно",
        "weekly": "еженедельно",
        "biweekly": "раз в 2 недели",
        "monthly": "ежемесячно",
        "weekdays": "по будням (пн-пт)",
        "custom_weekdays": "по определенным дням"
    }
    
    # Для некоторых типов не нужен интервал
    if recurrence_type in ["weekdays", "custom_weekdays"]:
        if recurrence_type == "weekdays":
            # Для будней сразу переходим к дате окончания
            context.user_data['recurrence_interval'] = 1
            await query.edit_message_text(
                f"🔄 Выбрано: {type_names[recurrence_type]}\n\n"
                f"🏁 Введите дату окончания повторений (или отправьте '-' для бесконечного повторения):\n\n"
                f"Форматы:\n"
                f"• `25.12.2024` - до 25 декабря 2024\n"
                f"• `25.12` - до 25 декабря текущего года\n"
                f"• `-` - без ограничений",
                parse_mode='Markdown'
            )
            return RECURRING_WAITING_END
        else:
            # Для кастомных дней переходим к выбору дней недели
            await query.edit_message_text(
                f"🔄 Выбрано: {type_names[recurrence_type]}\n\n"
                f"Выберите дни недели:"
            )
            
            # Создаем кнопки для выбора дней недели
            weekday_keyboard = [
                [
                    InlineKeyboardButton("Пн", callback_data="wd_0"),
                    InlineKeyboardButton("Вт", callback_data="wd_1"),
                    InlineKeyboardButton("Ср", callback_data="wd_2"),
                    InlineKeyboardButton("Чт", callback_data="wd_3")
                ],
                [
                    InlineKeyboardButton("Пт", callback_data="wd_4"),
                    InlineKeyboardButton("Сб", callback_data="wd_5"),
                    InlineKeyboardButton("Вс", callback_data="wd_6")
                ],
                [
                    InlineKeyboardButton("✅ Готово", callback_data="wd_done"),
                    InlineKeyboardButton("📋 К списку встреч", callback_data="back_to_meetings")
                ]
            ]
            weekday_markup = InlineKeyboardMarkup(weekday_keyboard)
            
            await query.edit_message_reply_markup(reply_markup=weekday_markup)
            context.user_data['selected_weekdays'] = []
            return RECURRING_WAITING_WEEKDAYS
    else:
        # Для остальных типов запрашиваем интервал
        await query.edit_message_text(
            f"🔄 Выбрано: {type_names[recurrence_type]}\n\n"
            f"Введите интервал повторения (число):\n"
            f"• 1 - каждый день/неделю/месяц\n"
            f"• 2 - через день/через неделю/через месяц\n"
            f"• 3 - каждые 3 дня/недели/месяца\n"
            f"И т.д."
        )
        return RECURRING_WAITING_INTERVAL

async def add_recurring_meeting_weekdays(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора дней недели"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "back_to_meetings":
        context.user_data.clear()
        await show_main_meetings_list(query, user.id)
        return ConversationHandler.END
    
    if query.data == "wd_done":
        selected_weekdays = context.user_data.get('selected_weekdays', [])
        if not selected_weekdays:
            await query.answer("Выберите хотя бы один день недели!", show_alert=True)
            return RECURRING_WAITING_WEEKDAYS
        
        # Сохраняем выбранные дни недели
        weekdays_str = ','.join(map(str, sorted(selected_weekdays)))
        context.user_data['recurrence_weekdays'] = weekdays_str
        context.user_data['recurrence_interval'] = 1
        
        # Переходим к дате окончания
        weekday_names = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']
        selected_names = [weekday_names[i] for i in selected_weekdays]
        
        await query.edit_message_text(
            f"🔄 Выбрано: по {', '.join(selected_names)}\n\n"
            f"🏁 Введите дату окончания повторений (или отправьте '-' для бесконечного повторения):\n\n"
            f"Форматы:\n"
            f"• `25.12.2024` - до 25 декабря 2024\n"
            f"• `25.12` - до 25 декабря текущего года\n"
            f"• `-` - без ограничений",
            parse_mode='Markdown'
        )
        return RECURRING_WAITING_END
    
    # Обработка выбора конкретного дня недели
    if query.data.startswith("wd_"):
        try:
            weekday = int(query.data.split("_")[1])
            selected_weekdays = context.user_data.get('selected_weekdays', [])
            
            if weekday in selected_weekdays:
                selected_weekdays.remove(weekday)
            else:
                selected_weekdays.append(weekday)
            
            context.user_data['selected_weekdays'] = selected_weekdays
            
            # Обновляем кнопки с отметками выбранных дней
            weekday_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
            weekday_keyboard = [
                [
                    InlineKeyboardButton(
                        f"{'✅ ' if 0 in selected_weekdays else ''}{weekday_names[0]}", 
                        callback_data="wd_0"
                    ),
                    InlineKeyboardButton(
                        f"{'✅ ' if 1 in selected_weekdays else ''}{weekday_names[1]}", 
                        callback_data="wd_1"
                    ),
                    InlineKeyboardButton(
                        f"{'✅ ' if 2 in selected_weekdays else ''}{weekday_names[2]}", 
                        callback_data="wd_2"
                    ),
                    InlineKeyboardButton(
                        f"{'✅ ' if 3 in selected_weekdays else ''}{weekday_names[3]}", 
                        callback_data="wd_3"
                    )
                ],
                [
                    InlineKeyboardButton(
                        f"{'✅ ' if 4 in selected_weekdays else ''}{weekday_names[4]}", 
                        callback_data="wd_4"
                    ),
                    InlineKeyboardButton(
                        f"{'✅ ' if 5 in selected_weekdays else ''}{weekday_names[5]}", 
                        callback_data="wd_5"
                    ),
                    InlineKeyboardButton(
                        f"{'✅ ' if 6 in selected_weekdays else ''}{weekday_names[6]}", 
                        callback_data="wd_6"
                    )
                ],
                [
                    InlineKeyboardButton("✅ Готово", callback_data="wd_done"),
                    InlineKeyboardButton("📋 К списку встреч", callback_data="back_to_meetings")
                ]
            ]
            weekday_markup = InlineKeyboardMarkup(weekday_keyboard)
            
            await query.edit_message_reply_markup(reply_markup=weekday_markup)
            
        except (ValueError, IndexError):
            pass
    
    return RECURRING_WAITING_WEEKDAYS

async def add_recurring_meeting_interval(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение интервала повторения"""
    try:
        interval = int(update.message.text.strip())
        if interval < 1:
            raise ValueError("Интервал должен быть больше 0")
        
        context.user_data['recurrence_interval'] = interval
        
        await update.message.reply_text(
            "🏁 Введите дату окончания повторений (или отправьте '-' для бесконечного повторения):\n\n"
            "Форматы:\n"
            "• `25.12.2024` - до 25 декабря 2024\n"
            "• `25.12` - до 25 декабря текущего года\n"
            "• `-` - без ограничений",
            parse_mode='Markdown'
        )
        
        return RECURRING_WAITING_END
        
    except ValueError:
        await update.message.reply_text(
            "⚠️ Введите корректное число (1, 2, 3, ...):"
        )
        return RECURRING_WAITING_INTERVAL

async def add_recurring_meeting_end(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение даты окончания и сохранение регулярной встречи"""
    user = update.effective_user
    end_str = update.message.text.strip()
    
    end_date = None
    if end_str != '-':
        try:
            # Парсим дату окончания
            if '.' in end_str:
                parts = end_str.split('.')
                if len(parts) == 2:  # ДД.ММ
                    day, month = map(int, parts)
                    year = datetime.now().year
                    end_date = datetime(year, month, day, 23, 59, 59)
                elif len(parts) == 3:  # ДД.ММ.ГГГГ
                    day, month, year = map(int, parts)
                    end_date = datetime(year, month, day, 23, 59, 59)
                else:
                    raise ValueError("Неверный формат даты")
            else:
                raise ValueError("Неверный формат даты")
            
            # Проверяем, что дата окончания в будущем
            if end_date <= datetime.now():
                await update.message.reply_text(
                    "⚠️ Дата окончания должна быть в будущем. Попробуйте еще раз:"
                )
                return RECURRING_WAITING_END
                
        except ValueError:
            await update.message.reply_text(
                "⚠️ Неверный формат даты. Используйте:\n"
                "• `25.12` - 25 декабря текущего года\n"
                "• `25.12.2024` - 25 декабря 2024 года\n"
                "• `-` - без ограничений",
                parse_mode='Markdown'
            )
            return RECURRING_WAITING_END
    
    # Сохраняем регулярную встречу
    try:
        title = context.user_data['recurring_title']
        description = context.user_data['recurring_description']
        meeting_time = context.user_data['recurring_time']
        recurrence_type = context.user_data['recurrence_type']
        interval = context.user_data['recurrence_interval']
        
        weekdays = context.user_data.get('recurrence_weekdays')
        
        meeting_id = db.add_meeting(
            user.id, title, description, meeting_time,
            is_recurring=True,
            recurrence_type=recurrence_type,
            recurrence_interval=interval,
            recurrence_weekdays=weekdays,
            recurrence_end_date=end_date
        )
        
        # Форматируем информацию для отображения
        time_display = meeting_time.strftime("%d.%m.%Y в %H:%M")
        
        if recurrence_type == "daily":
            recurrence_text = "ежедневно" if interval == 1 else f"каждые {interval} дня"
        elif recurrence_type == "weekly":
            recurrence_text = "еженедельно" if interval == 1 else f"каждые {interval} недели"
        elif recurrence_type == "biweekly":
            recurrence_text = "раз в 2 недели" if interval == 1 else f"каждые {2 * interval} недели"
        elif recurrence_type == "monthly":
            recurrence_text = "ежемесячно" if interval == 1 else f"каждые {interval} месяца"
        elif recurrence_type == "weekdays":
            recurrence_text = "по будням (пн-пт)"
        elif recurrence_type == "custom_weekdays" and weekdays:
            weekday_names = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']
            try:
                selected_days = [weekday_names[int(d)] for d in weekdays.split(',')]
                recurrence_text = f"по {', '.join(selected_days)}"
            except (ValueError, IndexError):
                recurrence_text = "по выбранным дням"
        else:
            recurrence_text = "регулярно"
        
        response = f"✅ Регулярная встреча успешно добавлена!\n\n"
        response += f"📝 Название: {title}\n"
        response += f"📄 Описание: {description if description else 'Не указано'}\n"
        response += f"🕐 Первая встреча: {time_display}\n"
        response += f"🔄 Повторяется: {recurrence_text}\n"
        
        if end_date:
            end_display = end_date.strftime("%d.%m.%Y")
            response += f"🏁 До: {end_display}\n"
        else:
            response += f"🏁 Без ограничений\n"
        
        response += f"🆔 ID встречи: {meeting_id}\n\n"
        
        # Получаем пользовательские настройки времени напоминания
        user_reminder_minutes = db.get_user_reminder_minutes(user.id)
        reminder_text = format_reminder_time(user_reminder_minutes)
        logger.info(f"Пользователь {user.id}: время напоминания для регулярной встречи {user_reminder_minutes} минут")
        response += f"🔔 Я буду напоминать вам за {reminder_text} до каждой встречи!"
        
        await update.message.reply_text(response)
        
        # Очищаем данные
        context.user_data.clear()
        
        logger.info(f"Пользователь {user.id} добавил регулярную встречу '{title}' ({recurrence_type}, интервал {interval})")
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Ошибка сохранения регулярной встречи: {e}")
        await update.message.reply_text("❌ Произошла ошибка при сохранении встречи.")
        return ConversationHandler.END

async def add_recurring_meeting_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена добавления регулярной встречи"""
    context.user_data.clear()
    await update.message.reply_text("❌ Добавление регулярной встречи отменено.")
    return ConversationHandler.END

# ============= КОНЕЦ ФУНКЦИЙ ДЛЯ РЕГУЛЯРНЫХ ВСТРЕЧ =============

# ============= КОНЕЦ ФУНКЦИЙ ДЛЯ ВСТРЕЧ =============

# ============= ФУНКЦИИ ДЛЯ НАСТРОЕК =============

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать настройки пользователя"""
    try:
        user = update.effective_user
        logger.info(f"Пользователь {user.id} запросил настройки")
        
        # Получаем текущие настройки пользователя
        user_settings = db.get_user_settings(user.id)
        reminder_minutes = user_settings['reminder_minutes']
        
        # Формируем текст с правильным склонением
        if reminder_minutes == 1:
            time_text = "1 минуту"
        elif reminder_minutes in [2, 3, 4]:
            time_text = f"{reminder_minutes} минуты"
        else:
            time_text = f"{reminder_minutes} минут"
        
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
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    logger.info(f"Пользователь {user.id} начал изменение времени напоминания")
    
    # Получаем текущие настройки
    user_settings = db.get_user_settings(user.id)
    current_minutes = user_settings['reminder_minutes']
    
    # Формируем текст с правильным склонением
    if current_minutes == 1:
        current_text = "1 минуту"
    elif current_minutes in [2, 3, 4]:
        current_text = f"{current_minutes} минуты"
    else:
        current_text = f"{current_minutes} минут"
    
    text = f"""
🔔 **Настройка времени напоминания**

Текущее значение: за {current_text} до встречи

Введите новое время в минутах (от 1 до 60):

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
    try:
        user = update.effective_user
        text = update.message.text.strip()
        
        # Проверяем, что введено число
        try:
            minutes = int(text)
        except ValueError:
            await update.message.reply_text(
                "❌ Пожалуйста, введите число от 1 до 60.\n\nПример: `5`",
                parse_mode='Markdown'
            )
            return SETTINGS_WAITING_REMINDER_TIME
        
        # Проверяем диапазон
        if minutes < 1 or minutes > 60:
            await update.message.reply_text(
                "❌ Время напоминания должно быть от 1 до 60 минут.\n\nПример: `5`",
                parse_mode='Markdown'
            )
            return SETTINGS_WAITING_REMINDER_TIME
        
        # Сохраняем настройки
        success = db.set_user_reminder_minutes(user.id, minutes)
        
        if success:
            # Формируем текст с правильным склонением
            if minutes == 1:
                time_text = "1 минуту"
            elif minutes in [2, 3, 4]:
                time_text = f"{minutes} минуты"
            else:
                time_text = f"{minutes} минут"
            
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
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    
    # Получаем текущие настройки пользователя
    user_settings = db.get_user_settings(user.id)
    reminder_minutes = user_settings['reminder_minutes']
    
    # Формируем текст с правильным склонением
    if reminder_minutes == 1:
        time_text = "1 минуту"
    elif reminder_minutes in [2, 3, 4]:
        time_text = f"{reminder_minutes} минуты"
    else:
        time_text = f"{reminder_minutes} минут"
    
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

# ============= КОНЕЦ ФУНКЦИЙ ДЛЯ НАСТРОЕК =============

async def shutdown_reminder_system():
    """Остановка системы напоминаний при завершении работы"""
    global reminder_system
    if reminder_system:
        await reminder_system.stop()

def main() -> None:
    """Запуск бота"""
    global db, reminder_system
    
    try:
        logger.info("Запуск бота...")
        
        # Инициализируем базу данных
        db = MeetingDatabase()
        logger.info("База данных инициализирована")
        
        # Создаем приложение с настройками для сервера
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Инициализируем систему напоминаний
        reminder_system = ReminderSystem(application.bot, db)
        
        # Добавляем обработчики основных команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("meow", meow))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("meetings", list_meetings))
        application.add_handler(CommandHandler("delete_meeting", delete_meeting))
        application.add_handler(CommandHandler("settings", settings_command))
        
        # Добавляем ConversationHandler для добавления встреч
        add_meeting_handler = ConversationHandler(
            entry_points=[
                CommandHandler("add_meeting", add_meeting_start),
                CallbackQueryHandler(add_meeting_type_callback, pattern="^add_regular$")
            ],
            states={
                WAITING_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_meeting_title)],
                WAITING_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_meeting_description)],
                WAITING_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_meeting_time)],
            },
            fallbacks=[CommandHandler("cancel", add_meeting_cancel)],
            per_message=False,
            per_chat=True
        )
        application.add_handler(add_meeting_handler)
        
        # Добавляем ConversationHandler для редактирования встреч
        edit_meeting_handler = ConversationHandler(
            entry_points=[
                CommandHandler("edit_meeting", edit_meeting_start),
                CallbackQueryHandler(edit_meeting_choice, pattern="^edit_(title|description|time|recurrence|enddate)_\\d+$")
            ],
            states={
                EDIT_WAITING_CHOICE: [
                    CallbackQueryHandler(edit_meeting_choice, pattern="^edit_"),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: EDIT_WAITING_CHOICE)
                ],
                EDIT_WAITING_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_meeting_title)],
                EDIT_WAITING_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_meeting_description)],
                EDIT_WAITING_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_meeting_time)],
                EDIT_WAITING_RECURRENCE: [CallbackQueryHandler(edit_meeting_recurrence, pattern="^recur_")],
                EDIT_WAITING_END_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_meeting_end_date)],
            },
            fallbacks=[CommandHandler("cancel", add_meeting_cancel)],
            per_message=False,
            per_chat=True
        )
        application.add_handler(edit_meeting_handler)
        
        # Добавляем ConversationHandler для регулярных встреч
        recurring_meeting_handler = ConversationHandler(
            entry_points=[
                CommandHandler("add_recurring", add_recurring_meeting_start),
                CallbackQueryHandler(add_meeting_type_callback, pattern="^add_recurring$")
            ],
            states={
                RECURRING_WAITING_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_recurring_meeting_title)],
                RECURRING_WAITING_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_recurring_meeting_description)],
                RECURRING_WAITING_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_recurring_meeting_time)],
                RECURRING_WAITING_TYPE: [CallbackQueryHandler(add_recurring_meeting_type, pattern="^recur_")],
                RECURRING_WAITING_INTERVAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_recurring_meeting_interval)],
                RECURRING_WAITING_WEEKDAYS: [CallbackQueryHandler(add_recurring_meeting_weekdays, pattern="^(wd_|back_to_meetings)")],
                RECURRING_WAITING_END: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_recurring_meeting_end)],
            },
            fallbacks=[CommandHandler("cancel", add_recurring_meeting_cancel)],
            per_message=False,
            per_chat=True
        )
        application.add_handler(recurring_meeting_handler)
        
        # Добавляем ConversationHandler для настроек
        settings_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(change_reminder_time_callback, pattern="^change_reminder_time$")
            ],
            states={
                SETTINGS_WAITING_REMINDER_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_reminder_time)],
            },
            fallbacks=[CommandHandler("cancel", settings_cancel)],
            per_message=False,
            per_chat=True
        )
        application.add_handler(settings_handler)
        
        # Добавляем обработчик для кнопок удаления встреч
        application.add_handler(CallbackQueryHandler(delete_meeting_callback, pattern="^delete_"))
        
        # Добавляем обработчики для интерактивных кнопок в списке встреч
        application.add_handler(CallbackQueryHandler(meetings_action_callback, pattern="^(action_add|action_edit_list|action_delete_list|back_to_meetings|edit_\\d+)$"))
        
        # Добавляем обработчик для кнопок настроек
        application.add_handler(CallbackQueryHandler(back_to_settings_callback, pattern="^back_to_settings$"))
        # Обработчик для кнопки "К списку встреч" больше не нужен отдельно, так как он обрабатывается в meetings_action_callback
        
        # Обработчик для кнопки "К списку встреч" в ConversationHandler (не входит в основной обработчик)
        application.add_handler(CallbackQueryHandler(edit_meeting_choice, pattern="^back_to_meetings$"))
        
        # Добавляем обработчик ошибок
        application.add_error_handler(error_handler)
        
        # Запускаем систему напоминаний
        async def post_init(application):
            await reminder_system.start()
            logger.info("Система напоминаний запущена")
        
        # Добавляем функцию остановки при завершении
        async def post_shutdown(application):
            await shutdown_reminder_system()
        
        application.post_init = post_init
        application.post_shutdown = post_shutdown

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