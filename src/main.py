"""Основной файл бота с модульной структурой"""

import logging
import signal
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters, CallbackQueryHandler

# Импорты модулей
from .config.settings import setup_logging, get_bot_token, DATABASE_PATH, POLLING_TIMEOUT, READ_TIMEOUT, WRITE_TIMEOUT
from .constants import (
    WAITING_TITLE, WAITING_DESCRIPTION, WAITING_TIME,
    EDIT_WAITING_CHOICE, EDIT_WAITING_TITLE, EDIT_WAITING_DESCRIPTION, 
    EDIT_WAITING_TIME, EDIT_WAITING_RECURRENCE, EDIT_WAITING_END_DATE, EDIT_WAITING_WEEKDAYS,
    RECURRING_WAITING_TITLE, RECURRING_WAITING_DESCRIPTION, RECURRING_WAITING_TIME, 
    RECURRING_WAITING_TYPE, RECURRING_WAITING_INTERVAL, RECURRING_WAITING_WEEKDAYS, RECURRING_WAITING_END,
    SETTINGS_WAITING_REMINDER_TIME, SETTINGS_WAITING_TIMEZONE
)
from .handlers.basic_commands import start, meow, help_command, error_handler
from .handlers.meetings import (
    add_meeting_start, add_meeting_title, add_meeting_description, 
    add_meeting_time, add_meeting_cancel, list_meetings, delete_meeting
)
from .handlers.edit_meetings import (
    edit_meeting_callback, edit_choice_callback, edit_title, 
    edit_description, edit_time, edit_cancel, back_to_edit_list_callback, edit_recurrence_type,
    edit_weekday_callback, finalize_weekdays_selection
)
from .handlers.settings import (
    settings_command, change_reminder_time_callback, set_reminder_time,
    back_to_settings_callback, settings_cancel, change_timezone_callback, set_timezone_callback
)
from .handlers.callbacks import delete_meeting_callback, meetings_action_callback, add_meeting_callback
from .handlers.recurring_meetings import (
    add_recurring_title, add_recurring_description, add_recurring_time,
    add_recurring_type, add_recurring_weekdays, add_recurring_cancel
)

# Импорты существующих модулей
from database import MeetingDatabase
from reminder_system import ReminderSystem

# Настройка логирования
setup_logging()
logger = logging.getLogger(__name__)

# Глобальные переменные
shutdown_requested = False
db = None
reminder_system = None


def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    global shutdown_requested
    logger.info(f"Получен сигнал {signum}, начинаем graceful shutdown...")
    shutdown_requested = True


# Регистрируем обработчики сигналов
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


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
        
        # Получаем токен бота
        bot_token = get_bot_token()
        
        # Инициализируем базу данных
        db = MeetingDatabase(DATABASE_PATH)
        logger.info("База данных инициализирована")
        
        # Создаем приложение с настройками для сервера
        application = Application.builder().token(bot_token).build()
        
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
                CallbackQueryHandler(add_meeting_callback, pattern="^add_regular$"),
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
        
        # Добавляем ConversationHandler для регулярных встреч
        recurring_meeting_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(add_meeting_callback, pattern="^add_recurring$"),
            ],
            states={
                RECURRING_WAITING_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_recurring_title)],
                RECURRING_WAITING_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_recurring_description)],
                RECURRING_WAITING_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_recurring_time)],
                RECURRING_WAITING_TYPE: [
                    CallbackQueryHandler(add_recurring_type, pattern="^recur_"),
                    CallbackQueryHandler(add_recurring_cancel, pattern="^cancel_recurring$")
                ],
                RECURRING_WAITING_WEEKDAYS: [
                    CallbackQueryHandler(add_recurring_weekdays, pattern="^weekday_\\d+$"),
                    CallbackQueryHandler(add_recurring_weekdays, pattern="^weekdays_done$"),
                    CallbackQueryHandler(add_recurring_cancel, pattern="^cancel_recurring$")
                ],
            },
            fallbacks=[
                CommandHandler("cancel", add_recurring_cancel),
                CallbackQueryHandler(add_recurring_cancel, pattern="^cancel_recurring$")
            ],
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
        
        # Добавляем ConversationHandler для редактирования встреч
        edit_meeting_handler = ConversationHandler(
            entry_points=[
                CallbackQueryHandler(edit_meeting_callback, pattern="^edit_\\d+$"),
            ],
            states={
                EDIT_WAITING_CHOICE: [
                    CallbackQueryHandler(edit_choice_callback, pattern="^edit_(title|description|time|recurrence|end_date)$"),
                    CallbackQueryHandler(back_to_edit_list_callback, pattern="^back_to_meetings$")
                ],
                EDIT_WAITING_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_title)],
                EDIT_WAITING_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_description)],
                EDIT_WAITING_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_time)],
                EDIT_WAITING_RECURRENCE: [
                    CallbackQueryHandler(edit_recurrence_type, pattern="^recur_type_"),
                    CallbackQueryHandler(back_to_edit_list_callback, pattern="^back_to_meetings$")
                ],
                EDIT_WAITING_WEEKDAYS: [
                    CallbackQueryHandler(edit_weekday_callback, pattern="^weekday_\\d+$"),
                    CallbackQueryHandler(finalize_weekdays_selection, pattern="^weekdays_done$"),
                    CallbackQueryHandler(back_to_edit_list_callback, pattern="^back_to_meetings$")
                ],
                EDIT_WAITING_END_DATE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, edit_title),  # Временно используем edit_title
                    CallbackQueryHandler(back_to_edit_list_callback, pattern="^back_to_meetings$")
                ],
            },
            fallbacks=[CommandHandler("cancel", edit_cancel)],
            per_message=False,
            per_chat=True
        )
        application.add_handler(edit_meeting_handler)
        
        # Добавляем обработчик для кнопок удаления встреч
        application.add_handler(CallbackQueryHandler(delete_meeting_callback, pattern="^delete_"))
        
        # Добавляем обработчики для интерактивных кнопок в списке встреч
        application.add_handler(CallbackQueryHandler(meetings_action_callback, pattern="^(action_add|action_edit_list|action_delete_list|back_to_meetings)$"))
        
        # Добавляем обработчик для кнопок настроек
        application.add_handler(CallbackQueryHandler(back_to_settings_callback, pattern="^back_to_settings$"))
        application.add_handler(CallbackQueryHandler(change_timezone_callback, pattern="^change_timezone$"))
        application.add_handler(CallbackQueryHandler(set_timezone_callback, pattern="^set_tz_"))
        
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
            timeout=POLLING_TIMEOUT,
            read_timeout=READ_TIMEOUT,
            write_timeout=WRITE_TIMEOUT,
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
