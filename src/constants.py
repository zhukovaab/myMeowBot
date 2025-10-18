"""Константы для бота"""

# Состояния для ConversationHandler
WAITING_TITLE, WAITING_DESCRIPTION, WAITING_TIME = range(3)
EDIT_WAITING_CHOICE, EDIT_WAITING_TITLE, EDIT_WAITING_DESCRIPTION, EDIT_WAITING_TIME, EDIT_WAITING_RECURRENCE, EDIT_WAITING_END_DATE = range(4, 10)

# Состояния для регулярных встреч
RECURRING_WAITING_TITLE, RECURRING_WAITING_DESCRIPTION, RECURRING_WAITING_TIME, RECURRING_WAITING_TYPE, RECURRING_WAITING_INTERVAL, RECURRING_WAITING_WEEKDAYS, RECURRING_WAITING_END = range(15, 22)

# Состояния для настроек
SETTINGS_WAITING_REMINDER_TIME = 22

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
