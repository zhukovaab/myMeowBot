import asyncio
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import pytz
from telegram import Bot
from telegram.error import TelegramError
from database import MeetingDatabase

logger = logging.getLogger(__name__)

class ReminderSystem:
    def __init__(self, bot: Bot, db: MeetingDatabase):
        self.bot = bot
        self.db = db
        self.running = False
        self.task = None
        self.sent_reminders = set()  # Отслеживание отправленных напоминаний
    
    async def start(self):
        """Запуск системы напоминаний"""
        if self.running:
            return
        
        self.running = True
        self.task = asyncio.create_task(self._reminder_loop())
        logger.info("Система напоминаний запущена")
    
    async def stop(self):
        """Остановка системы напоминаний"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("Система напоминаний остановлена")
    
    async def _reminder_loop(self):
        """Основной цикл проверки напоминаний"""
        while self.running:
            try:
                await self._check_and_send_reminders()
                # Проверяем каждые 30 секунд
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле напоминаний: {e}")
                await asyncio.sleep(60)  # При ошибке ждем дольше
    
    async def _check_and_send_reminders(self):
        """Проверка и отправка напоминаний"""
        try:
            # Получаем всех пользователей, у которых есть встречи
            users_with_meetings = self.db.get_all_users_with_meetings()
            
            # Текущее время в UTC (так как встречи сохранены в UTC)
            now_utc = datetime.utcnow()
            
            # Проверяем каждого пользователя с его индивидуальными настройками
            for user_id in users_with_meetings:
                user_reminder_minutes = self.db.get_user_reminder_minutes(user_id)
                
                # Получаем встречи этого пользователя, для которых нужно отправить напоминание
                meetings_for_reminder = self.db.get_meetings_for_reminder(user_id, user_reminder_minutes)
                
                for meeting in meetings_for_reminder:
                    # Время встречи в UTC
                    meeting_time_utc = datetime.fromisoformat(meeting['meeting_time'])
                    reminder_time_utc = meeting_time_utc - timedelta(minutes=user_reminder_minutes)
                    
                    # Проверяем, нужно ли отправить напоминание сейчас
                    if now_utc >= reminder_time_utc and now_utc < meeting_time_utc:
                        # Создаем уникальный ключ для напоминания
                        reminder_key = f"{meeting['id']}_{meeting['meeting_time']}_{user_reminder_minutes}"
                        
                        # Проверяем, не отправляли ли уже это напоминание
                        if reminder_key not in self.sent_reminders:
                            await self._send_reminder(meeting, user_reminder_minutes)
                            self.sent_reminders.add(reminder_key)
                            
                            # Очищаем старые записи (старше 2 часов)
                            if len(self.sent_reminders) > 1000:
                                self.sent_reminders.clear()
            
            # Обрабатываем регулярные встречи (каждые 5 минут)
            if not hasattr(self, '_last_recurring_check'):
                self._last_recurring_check = 0
            
            import time
            current_time = time.time()
            if current_time - self._last_recurring_check > 300:  # 5 минут
                await self._process_recurring_meetings()
                await self._cleanup_past_meetings()
                self._last_recurring_check = current_time
                
        except Exception as e:
            logger.error(f"Ошибка при проверке напоминаний: {e}")
    
    async def _process_recurring_meetings(self):
        """Обработка регулярных встреч"""
        try:
            recurring_meetings = self.db.get_recurring_meetings_to_process()
            
            for meeting in recurring_meetings:
                next_meeting_id = self.db.create_next_recurring_meeting(meeting)
                if next_meeting_id:
                    logger.info(f"Создана следующая встреча в серии регулярных встреч: ID {next_meeting_id}")
                    
        except Exception as e:
            logger.error(f"Ошибка при обработке регулярных встреч: {e}")
    
    async def _cleanup_past_meetings(self):
        """Очистка прошедших встреч"""
        try:
            deleted_count = self.db.cleanup_past_meetings()
            if deleted_count > 0:
                logger.info(f"Автоматически удалено {deleted_count} прошедших встреч")
                
        except Exception as e:
            logger.error(f"Ошибка при очистке прошедших встреч: {e}")
    
    async def _get_cat_image_url(self) -> Optional[str]:
        """Получение URL картинки котика из The Cat API"""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get('https://api.thecatapi.com/v1/images/search', timeout=10)
                response.raise_for_status()
                
                cat_data = response.json()
                if cat_data and len(cat_data) > 0:
                    return cat_data[0]['url']
            
        except httpx.RequestError as e:
            logger.error(f"Ошибка получения картинки котика: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при получении картинки котика: {e}")
        
        return None
    
    async def _send_reminder(self, meeting: Dict[str, Any], reminder_minutes: int = 2):
        """Отправка напоминания о встрече"""
        try:
            user_id = meeting['user_id']
            title = meeting['title']
            description = meeting['description']
            
            # Время встречи в UTC
            meeting_time_utc = datetime.fromisoformat(meeting['meeting_time'])
            
            # Получаем часовой пояс пользователя и конвертируем время
            user_timezone = self.db.get_user_timezone(user_id)
            try:
                tz = pytz.timezone(user_timezone)
                # Конвертируем UTC время в часовой пояс пользователя
                meeting_time_user = pytz.utc.localize(meeting_time_utc).astimezone(tz)
            except pytz.UnknownTimeZoneError:
                # Fallback на московское время
                tz = pytz.timezone('Europe/Moscow')
                meeting_time_user = pytz.utc.localize(meeting_time_utc).astimezone(tz)
            
            # Форматируем время в часовом поясе пользователя
            time_str = meeting_time_user.strftime("%H:%M")
            
            # Создаем текст напоминания
            reminder_text = f"🔔 {title}!\n\n"
            reminder_text += f"📅 Время: {time_str}\n"
            
            if description:
                reminder_text += f"📄 Описание: {description}\n"
            
            # Добавляем информацию о регулярности
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
                
                reminder_text += f"🔄 Повторяется: {recurrence_text}\n"
            
            # Формируем текст с правильным временем
            if reminder_minutes == 1:
                time_text = "1 минуту"
            elif reminder_minutes in [2, 3, 4]:
                time_text = f"{reminder_minutes} минуты"
            else:
                time_text = f"{reminder_minutes} минут"
            
            reminder_text += f"\n⏰ Встреча начнется через {time_text}!"
            
            # Получаем картинку котика
            cat_image_url = await self._get_cat_image_url()
            
            if cat_image_url:
                # Отправляем напоминание с картинкой котика
                try:
                    await self.bot.send_photo(
                        chat_id=user_id,
                        photo=cat_image_url,
                        caption=reminder_text
                    )
                except TelegramError as e:
                    # Если не удалось отправить картинку, отправляем только текст
                    logger.warning(f"Не удалось отправить картинку котика: {e}")
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=f"🐱 {reminder_text}"
                    )
            else:
                # Отправляем напоминание без картинки, но с эмодзи котика
                await self.bot.send_message(
                    chat_id=user_id,
                    text=f"🐱 {reminder_text}"
                )
            
            logger.info(f"Отправлено напоминание пользователю {user_id} о встрече '{title}'")
            
        except TelegramError as e:
            logger.error(f"Ошибка отправки напоминания пользователю {meeting['user_id']}: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке напоминания: {e}")
    
    def format_meeting_time(self, meeting_time: datetime) -> str:
        """Форматирование времени встречи для отображения"""
        now = datetime.now()
        
        # Если встреча сегодня
        if meeting_time.date() == now.date():
            return f"сегодня в {meeting_time.strftime('%H:%M')}"
        
        # Если встреча завтра
        elif meeting_time.date() == (now + timedelta(days=1)).date():
            return f"завтра в {meeting_time.strftime('%H:%M')}"
        
        # Если встреча в другой день
        else:
            return meeting_time.strftime("%d.%m.%Y в %H:%M")
