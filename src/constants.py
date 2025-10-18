"""Константы для бота"""

# Состояния для ConversationHandler
WAITING_TITLE, WAITING_DESCRIPTION, WAITING_TIME = range(3)
EDIT_WAITING_CHOICE, EDIT_WAITING_TITLE, EDIT_WAITING_DESCRIPTION, EDIT_WAITING_TIME, EDIT_WAITING_RECURRENCE, EDIT_WAITING_END_DATE, EDIT_WAITING_WEEKDAYS = range(4, 11)

# Состояния для регулярных встреч
RECURRING_WAITING_TITLE, RECURRING_WAITING_DESCRIPTION, RECURRING_WAITING_TIME, RECURRING_WAITING_TYPE, RECURRING_WAITING_INTERVAL, RECURRING_WAITING_WEEKDAYS, RECURRING_WAITING_END = range(11, 18)

# Состояния для настроек
SETTINGS_WAITING_REMINDER_TIME = 18
SETTINGS_WAITING_TIMEZONE = 19

# Типы повторения встреч
RECURRENCE_TYPES = {
    "recur_daily": "daily",
    "recur_weekly": "weekly", 
    "recur_biweekly": "biweekly",
    "recur_monthly": "monthly",
    "recur_weekdays": "weekdays",
    "recur_custom": "custom_weekdays"
}

# Названия типов повторения
TYPE_NAMES = {
    "daily": "ежедневно",
    "weekly": "еженедельно",
    "biweekly": "раз в 2 недели",
    "monthly": "ежемесячно",
    "weekdays": "по будням (пн-пт)",
    "custom_weekdays": "по определенным дням"
}

# Названия дней недели
WEEKDAY_NAMES = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']
WEEKDAY_NAMES_FULL = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

# Настройки по умолчанию
DEFAULT_REMINDER_MINUTES = 2
MAX_REMINDER_MINUTES = 60
MIN_REMINDER_MINUTES = 1

# Ограничения безопасности
MAX_TITLE_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 1000
MAX_MEETINGS_PER_DAY = 50

# API настройки
CAT_API_URL = 'https://api.thecatapi.com/v1/images/search'
REQUEST_TIMEOUT = 15

# Часовые пояса по времени от UTC-12 до UTC+12
POPULAR_TIMEZONES = {
    'Pacific/Auckland': 'UTC+12 (Окленд)',
    'Asia/Vladivostok': 'UTC+10 (Владивосток)',
    'Asia/Tokyo': 'UTC+9 (Токио)',
    'Asia/Irkutsk': 'UTC+8 (Иркутск)',
    'Asia/Krasnoyarsk': 'UTC+7 (Красноярск)',
    'Asia/Almaty': 'UTC+6 (Алматы)',
    'Asia/Yekaterinburg': 'UTC+5 (Екатеринбург)',
    'Asia/Dubai': 'UTC+4 (Дубай)',
    'Europe/Moscow': 'UTC+3 (Москва)',
    'Europe/Kiev': 'UTC+2 (Киев)',
    'Europe/Berlin': 'UTC+1 (Берлин)',
    'Europe/London': 'UTC+0 (Лондон)',
    'America/New_York': 'UTC-5 (Нью-Йорк)',
    'America/Los_Angeles': 'UTC-8 (Лос-Анджелес)',
    'Pacific/Honolulu': 'UTC-10 (Гонолулу)'
}
