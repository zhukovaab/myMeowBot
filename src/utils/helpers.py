"""Вспомогательные функции"""

import re
from datetime import datetime, timedelta
from typing import Optional

from ..constants import WEEKDAY_NAMES


def format_reminder_time(minutes: int) -> str:
    """Форматирует время напоминания с правильным склонением"""
    if minutes == 1:
        return "1 минуту"
    elif minutes in [2, 3, 4]:
        return f"{minutes} минуты"
    else:
        return f"{minutes} минут"


def parse_datetime(date_str: str) -> datetime:
    """Парсинг строки с датой и временем"""
    # Убираем лишние пробелы
    date_str = date_str.strip()
    
    # Предварительная обработка: заменяем пробел между цифрами времени на двоеточие
    # Паттерн для времени через пробел: цифры пробел цифры (в конце строки или перед пробелом)
    import re
    # Заменяем "15 30" на "15:30", "завтра 15 30" на "завтра 15:30" и т.д.
    date_str = re.sub(r'(\d{1,2})\s+(\d{1,2})(?=\s|$)', r'\1:\2', date_str)
    
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
