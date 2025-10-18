"""Вспомогательные функции"""

import re
from datetime import datetime, timedelta
from typing import Optional
import pytz

from ..constants import WEEKDAY_NAMES


def format_reminder_time(minutes: int) -> str:
    """Форматирует время напоминания с правильным склонением"""
    if minutes == 1:
        return "1 минуту"
    elif minutes in [2, 3, 4]:
        return f"{minutes} минуты"
    else:
        return f"{minutes} минут"


def format_meeting_time_for_user(meeting_time_utc: datetime, user_timezone: str = 'Europe/Moscow') -> str:
    """Форматирует время встречи в часовом поясе пользователя"""
    try:
        tz = pytz.timezone(user_timezone)
        # Конвертируем UTC время в часовой пояс пользователя
        if isinstance(meeting_time_utc, str):
            meeting_time_utc = datetime.fromisoformat(meeting_time_utc)
        
        # Локализуем UTC время и конвертируем в часовой пояс пользователя
        utc_time = pytz.utc.localize(meeting_time_utc)
        local_time = utc_time.astimezone(tz)
        
        return local_time.strftime("%d.%m.%Y в %H:%M")
    except (pytz.UnknownTimeZoneError, ValueError):
        # Fallback на UTC отображение
        if isinstance(meeting_time_utc, str):
            meeting_time_utc = datetime.fromisoformat(meeting_time_utc)
        return meeting_time_utc.strftime("%d.%m.%Y в %H:%M")


def parse_datetime(date_str: str, user_timezone: str = 'Europe/Moscow') -> datetime:
    """Парсинг строки с датой и временем с учетом часового пояса пользователя"""
    # Убираем лишние пробелы
    date_str = date_str.strip()
    
    # Получаем часовой пояс пользователя
    try:
        tz = pytz.timezone(user_timezone)
    except pytz.UnknownTimeZoneError:
        tz = pytz.timezone('Europe/Moscow')  # Fallback
    
    # Предварительная обработка: заменяем пробел между цифрами времени на двоеточие
    # Паттерн для времени через пробел: цифры пробел цифры (в конце строки или перед пробелом)
    import re
    # Заменяем "15 30" на "15:30", "завтра 15 30" на "завтра 15:30" и т.д.
    # Ищем последнюю пару цифр через пробел (это время)
    date_str = re.sub(r'(\d{1,2})\s+(\d{1,2})(?=\s*$)', r'\1:\2', date_str)
    
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
                    # Завтра в часовом поясе пользователя
                    hour, minute = map(int, match.groups())
                    # Получаем текущее время в часовом поясе пользователя
                    now_user_tz = datetime.now(tz)
                    tomorrow = now_user_tz + timedelta(days=1)
                    result = tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    # Конвертируем в UTC для сохранения в БД
                    return result.astimezone(pytz.UTC).replace(tzinfo=None)
                elif fmt == '%H:%M':
                    # Сегодня в часовом поясе пользователя
                    hour, minute = map(int, match.groups())
                    # Получаем текущее время в часовом поясе пользователя
                    now_user_tz = datetime.now(tz)
                    result = now_user_tz.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    # Если время уже прошло сегодня, переносим на завтра
                    if result <= now_user_tz:
                        result += timedelta(days=1)
                    # Конвертируем в UTC для сохранения в БД
                    return result.astimezone(pytz.UTC).replace(tzinfo=None)
                elif fmt == '%d.%m %H:%M':
                    # Текущий год в часовом поясе пользователя
                    day, month, hour, minute = map(int, match.groups())
                    year = datetime.now(tz).year
                    # Создаем время в часовом поясе пользователя
                    result = tz.localize(datetime(year, month, day, hour, minute))
                    # Конвертируем в UTC для сохранения в БД
                    return result.astimezone(pytz.UTC).replace(tzinfo=None)
                else:
                    # Полная дата в часовом поясе пользователя
                    naive_dt = datetime.strptime(date_str, fmt)
                    # Локализуем в часовом поясе пользователя
                    localized_dt = tz.localize(naive_dt)
                    # Конвертируем в UTC для сохранения в БД
                    return localized_dt.astimezone(pytz.UTC).replace(tzinfo=None)
            except ValueError:
                continue
    
    raise ValueError("Неверный формат даты и времени")


def format_recurrence_info(meeting: dict) -> str:
    """Форматирует информацию о повторении встречи"""
    if not meeting.get('is_recurring'):
        return ""
    
    recurrence_type = meeting.get('recurrence_type', '')
    interval = meeting.get('recurrence_interval', 1)
    weekdays = meeting.get('recurrence_weekdays')
    
    if recurrence_type == 'daily':
        if interval == 1:
            return "ежедневно"
        else:
            return f"каждые {interval} дня"
    elif recurrence_type == 'weekly':
        if interval == 1:
            return "еженедельно"
        else:
            return f"каждые {interval} недели"
    elif recurrence_type == 'biweekly':
        if interval == 1:
            return "раз в 2 недели"
        else:
            return f"каждые {2 * interval} недели"
    elif recurrence_type == 'monthly':
        if interval == 1:
            return "ежемесячно"
        else:
            return f"каждые {interval} месяца"
    elif recurrence_type == 'weekdays':
        return "по будням (пн-пт)"
    elif recurrence_type == 'custom_weekdays' and weekdays:
        try:
            selected_days = [WEEKDAY_NAMES[int(d)] for d in weekdays.split(',')]
            return f"по {', '.join(selected_days)}"
        except (ValueError, IndexError):
            return "по выбранным дням"
    else:
        return "регулярно"


def parse_end_date(date_str: str) -> Optional[datetime]:
    """Парсит дату окончания из строки"""
    if date_str == '-':
        return None
    
    if '.' in date_str:
        parts = date_str.split('.')
        if len(parts) == 2:  # DD.MM
            day, month = int(parts[0]), int(parts[1])
            year = datetime.now().year
            return datetime(year, month, day, 23, 59, 59)
        elif len(parts) == 3:  # DD.MM.YYYY
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            return datetime(year, month, day, 23, 59, 59)
    
    raise ValueError("Неверный формат даты")
