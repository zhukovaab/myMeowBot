"""Конфигурация бота"""

import os
import logging

# Попытка загрузить переменные из .env файла
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def setup_logging():
    """Настройка логирования с ротацией и автоматической очисткой"""
    from ..utils.logging_manager import setup_logging as setup_advanced_logging
    
    # Определяем параметры логирования из переменных окружения
    log_level_str = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    log_to_file = os.getenv('LOG_TO_FILE', 'true').lower() == 'true'
    log_to_console = os.getenv('LOG_TO_CONSOLE', 'true').lower() == 'true'
    log_dir = os.getenv('LOG_DIR', 'logs')
    max_days = int(os.getenv('LOG_MAX_DAYS', '1'))  # По умолчанию удаляем каждый день
    
    # Настраиваем продвинутое логирование
    setup_advanced_logging(
        log_level=log_level,
        log_to_file=log_to_file,
        log_to_console=log_to_console,
        log_dir=log_dir,
        max_days=max_days
    )


def get_bot_token() -> str:
    """Получение токена бота из переменной окружения"""
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        raise ValueError(
            "Не установлена переменная окружения BOT_TOKEN. "
            "Создайте файл .env с BOT_TOKEN=your_token или установите переменную окружения."
        )
    return bot_token


# Настройки базы данных
DATABASE_PATH = "meetings.db"

# Настройки polling
POLLING_TIMEOUT = 30
READ_TIMEOUT = 30
WRITE_TIMEOUT = 30
