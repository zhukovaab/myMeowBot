import sqlite3
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

class MeetingDatabase:
    def __init__(self, db_path: str = "meetings.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных и создание таблиц"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Создаем таблицу с базовой схемой
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS meetings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        title TEXT NOT NULL,
                        description TEXT,
                        meeting_time DATETIME NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Создаем таблицу пользовательских настроек
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_settings (
                        user_id INTEGER PRIMARY KEY,
                        reminder_minutes INTEGER DEFAULT 2,
                        timezone TEXT DEFAULT 'Europe/Moscow',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Проверяем и добавляем новые колонки если их нет
                self._migrate_database(cursor)
                
                conn.commit()
                logger.info("База данных встреч инициализирована")
        except sqlite3.Error as e:
            logger.error(f"Ошибка инициализации базы данных: {e}")
            raise
    
    def _migrate_database(self, cursor):
        """Миграция базы данных для добавления новых колонок"""
        # Получаем список существующих колонок в meetings
        cursor.execute("PRAGMA table_info(meetings)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        
        # Список новых колонок для регулярных встреч
        new_columns = [
            ("is_recurring", "BOOLEAN DEFAULT 0"),
            ("recurrence_type", "TEXT"),
            ("recurrence_interval", "INTEGER DEFAULT 1"),
            ("recurrence_weekdays", "TEXT"),
            ("recurrence_end_date", "DATETIME")
        ]
        
        # Добавляем отсутствующие колонки в meetings
        for column_name, column_definition in new_columns:
            if column_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE meetings ADD COLUMN {column_name} {column_definition}")
                    logger.info(f"Добавлена колонка {column_name} в таблицу meetings")
                except sqlite3.Error as e:
                    logger.error(f"Ошибка добавления колонки {column_name}: {e}")
                    raise
        
        # Миграция для user_settings - добавляем timezone если его нет
        try:
            cursor.execute("PRAGMA table_info(user_settings)")
            settings_columns = [column[1] for column in cursor.fetchall()]
            
            if "timezone" not in settings_columns:
                cursor.execute("ALTER TABLE user_settings ADD COLUMN timezone TEXT DEFAULT 'Europe/Moscow'")
                logger.info("Добавлена колонка timezone в таблицу user_settings")
        except sqlite3.Error as e:
            logger.error(f"Ошибка миграции user_settings: {e}")
            raise
    
    def add_meeting(self, user_id: int, title: str, description: str, meeting_time: datetime, 
                   is_recurring: bool = False, recurrence_type: str = None, 
                   recurrence_interval: int = 1, recurrence_weekdays: str = None,
                   recurrence_end_date: datetime = None) -> int:
        """Добавление новой встречи"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO meetings (user_id, title, description, meeting_time, 
                                        is_recurring, recurrence_type, recurrence_interval, 
                                        recurrence_weekdays, recurrence_end_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, title, description, meeting_time, 
                     is_recurring, recurrence_type, recurrence_interval, 
                     recurrence_weekdays, recurrence_end_date))
                meeting_id = cursor.lastrowid
                conn.commit()
                
                meeting_type = "регулярную" if is_recurring else "обычную"
                logger.info(f"Добавлена {meeting_type} встреча ID {meeting_id} для пользователя {user_id}")
                return meeting_id
        except sqlite3.Error as e:
            logger.error(f"Ошибка добавления встречи: {e}")
            raise
    
    def get_user_meetings(self, user_id: int) -> List[Dict[str, Any]]:
        """Получение всех встреч пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM meetings 
                    WHERE user_id = ? 
                    ORDER BY meeting_time ASC
                ''', (user_id,))
                meetings = [dict(row) for row in cursor.fetchall()]
                return meetings
        except sqlite3.Error as e:
            logger.error(f"Ошибка получения встреч пользователя {user_id}: {e}")
            return []
    
    def get_meeting_by_id(self, meeting_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение встречи по ID (только для конкретного пользователя)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT * FROM meetings 
                    WHERE id = ? AND user_id = ?
                ''', (meeting_id, user_id))
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Ошибка получения встречи {meeting_id}: {e}")
            return None
    
    
    def delete_meeting(self, meeting_id: int, user_id: int) -> bool:
        """Удаление встречи"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM meetings 
                    WHERE id = ? AND user_id = ?
                ''', (meeting_id, user_id))
                
                if cursor.rowcount > 0:
                    conn.commit()
                    logger.info(f"Удалена встреча ID {meeting_id} для пользователя {user_id}")
                    return True
                else:
                    return False
                    
        except sqlite3.Error as e:
            logger.error(f"Ошибка удаления встречи {meeting_id}: {e}")
            return False
    
    def get_upcoming_meetings(self, minutes_ahead: int = 60) -> List[Dict[str, Any]]:
        """Получение встреч, которые начнутся в ближайшее время (для проверки напоминаний)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Получаем все встречи, которые начнутся в течение следующих minutes_ahead минут (UTC)
                current_utc = datetime.utcnow()
                future_utc = (current_utc + timedelta(minutes=minutes_ahead)).strftime('%Y-%m-%d %H:%M:%S')
                current_utc_str = current_utc.strftime('%Y-%m-%d %H:%M:%S')
                
                cursor.execute('''
                    SELECT * FROM meetings 
                    WHERE meeting_time > ? AND meeting_time <= ?
                ''', (current_utc_str, future_utc))
                
                meetings = [dict(row) for row in cursor.fetchall()]
                return meetings
                
        except sqlite3.Error as e:
            logger.error(f"Ошибка получения предстоящих встреч: {e}")
            return []
    
    def get_meetings_for_reminder(self, user_id: int, reminder_minutes: int) -> List[Dict[str, Any]]:
        """Получение всех будущих встреч пользователя (проверка времени напоминания делается в reminder_system)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Получаем все будущие встречи пользователя (проверку времени делаем в reminder_system)
                current_utc = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute('''
                    SELECT * FROM meetings 
                    WHERE user_id = ? AND meeting_time > ?
                    ORDER BY meeting_time
                ''', (user_id, current_utc))
                
                meetings = [dict(row) for row in cursor.fetchall()]
                return meetings
                
        except sqlite3.Error as e:
            logger.error(f"Ошибка получения встреч для напоминания пользователю {user_id}: {e}")
            return []
    
    def cleanup_past_meetings(self) -> int:
        """Удаление прошедших встреч (кроме регулярных)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Используем UTC время, так как встречи теперь сохранены в UTC
                current_utc = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute('''
                    DELETE FROM meetings 
                    WHERE meeting_time < ?
                    AND (is_recurring = 0 OR is_recurring IS NULL)
                ''', (current_utc,))
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    logger.info(f"Удалено {deleted_count} прошедших встреч")
                
                return deleted_count
                
        except sqlite3.Error as e:
            logger.error(f"Ошибка при очистке прошедших встреч: {e}")
            return 0
    
    def get_user_reminder_minutes(self, user_id: int) -> int:
        """Получение времени напоминания для пользователя (в минутах)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT reminder_minutes FROM user_settings WHERE user_id = ?",
                    (user_id,)
                )
                result = cursor.fetchone()
                return result[0] if result else 2  # По умолчанию 2 минуты
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении настроек пользователя {user_id}: {e}")
            return 2  # По умолчанию 2 минуты
    
    def set_user_reminder_minutes(self, user_id: int, minutes: int) -> bool:
        """Установка времени напоминания для пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO user_settings (user_id, reminder_minutes, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, minutes))
                conn.commit()
                logger.info(f"Настройки пользователя {user_id} обновлены: напоминание за {minutes} минут")
                return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка при обновлении настроек пользователя {user_id}: {e}")
            return False
    
    def get_user_timezone(self, user_id: int) -> str:
        """Получение часового пояса пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT timezone FROM user_settings WHERE user_id = ?", (user_id,))
                result = cursor.fetchone()
                return result[0] if result else 'Europe/Moscow'
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении часового пояса пользователя {user_id}: {e}")
            return 'Europe/Moscow'
    
    def set_user_timezone(self, user_id: int, timezone: str) -> bool:
        """Установка часового пояса для пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO user_settings (user_id, timezone, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (user_id, timezone))
                conn.commit()
                logger.info(f"Часовой пояс пользователя {user_id} обновлен: {timezone}")
                return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка при обновлении часового пояса пользователя {user_id}: {e}")
            return False
    
    def get_user_settings(self, user_id: int) -> Dict[str, Any]:
        """Получение всех настроек пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT reminder_minutes, timezone, created_at, updated_at FROM user_settings WHERE user_id = ?",
                    (user_id,)
                )
                result = cursor.fetchone()
                if result:
                    return {
                        'reminder_minutes': result[0],
                        'timezone': result[1] or 'Europe/Moscow',
                        'created_at': result[2],
                        'updated_at': result[3]
                    }
                else:
                    # Создаем настройки по умолчанию
                    self.set_user_reminder_minutes(user_id, 2)
                    return {'reminder_minutes': 2, 'timezone': 'Europe/Moscow', 'created_at': None, 'updated_at': None}
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении настроек пользователя {user_id}: {e}")
            return {'reminder_minutes': 2, 'created_at': None, 'updated_at': None}
    
    def get_all_users_with_meetings(self) -> List[int]:
        """Получение списка всех пользователей, у которых есть встречи"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Получаем пользователей с будущими встречами (UTC)
                current_utc = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute(
                    "SELECT DISTINCT user_id FROM meetings WHERE meeting_time > ?", (current_utc,)
                )
                users = [row[0] for row in cursor.fetchall()]
                return users
        except sqlite3.Error as e:
            logger.error(f"Ошибка при получении пользователей с встречами: {e}")
            return []
    
    def get_recurring_meetings_to_process(self) -> List[Dict[str, Any]]:
        """Получение регулярных встреч, которые нужно обработать"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Используем UTC время, так как встречи теперь сохранены в UTC
                current_utc = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute('''
                    SELECT * FROM meetings 
                    WHERE is_recurring = 1 
                    AND meeting_time < ?
                    AND (recurrence_end_date IS NULL OR recurrence_end_date > ?)
                ''', (current_utc, current_utc))
                
                meetings = [dict(row) for row in cursor.fetchall()]
                return meetings
                
        except sqlite3.Error as e:
            logger.error(f"Ошибка получения регулярных встреч: {e}")
            return []
    
    def create_next_recurring_meeting(self, meeting: Dict[str, Any]) -> Optional[int]:
        """Создание следующей встречи в серии регулярных встреч"""
        try:
            from datetime import timedelta
            
            current_time = datetime.fromisoformat(meeting['meeting_time'])
            recurrence_type = meeting['recurrence_type']
            interval = meeting['recurrence_interval']
            weekdays = meeting.get('recurrence_weekdays')
            
            next_time = None
            
            # Вычисляем следующее время встречи
            if recurrence_type == 'daily':
                next_time = current_time + timedelta(days=interval)
            elif recurrence_type == 'weekly':
                next_time = current_time + timedelta(weeks=interval)
            elif recurrence_type == 'biweekly':
                next_time = current_time + timedelta(weeks=2 * interval)
            elif recurrence_type == 'monthly':
                # Приблизительно месяц = 30 дней
                next_time = current_time + timedelta(days=30 * interval)
            elif recurrence_type == 'weekdays':
                # Только по будням (пн-пт)
                # Если текущее время уже на выходном, найти следующий рабочий день
                if current_time.weekday() >= 5:  # суббота или воскресенье
                    # Найти следующий понедельник
                    from datetime import timedelta
                    days_until_monday = (7 - current_time.weekday()) % 7
                    if days_until_monday == 0:  # если сегодня воскресенье
                        days_until_monday = 1
                    next_time = current_time + timedelta(days=days_until_monday)
                else:
                    next_time = self._find_next_weekday(current_time)
            elif recurrence_type == 'custom_weekdays' and weekdays:
                # По определенным дням недели
                next_time = self._find_next_custom_weekday(current_time, weekdays)
            else:
                logger.error(f"Неизвестный тип повторения: {recurrence_type}")
                return None
            
            if not next_time:
                logger.error(f"Не удалось вычислить следующее время для встречи ID {meeting['id']}")
                return None
            
            # Проверяем, не превышает ли дата окончания
            end_date = meeting.get('recurrence_end_date')
            if end_date and next_time > datetime.fromisoformat(end_date):
                logger.info(f"Регулярная встреча ID {meeting['id']} завершена (достигнута дата окончания)")
                return None
            
            # Обновляем время текущей встречи
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE meetings 
                    SET meeting_time = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (next_time, meeting['id']))
                conn.commit()
                
                logger.info(f"Обновлено время регулярной встречи ID {meeting['id']} на {next_time}")
                return meeting['id']
                
        except Exception as e:
            logger.error(f"Ошибка создания следующей регулярной встречи: {e}")
            return None
    
    def _find_next_weekday(self, current_time: datetime) -> datetime:
        """Найти следующий рабочий день (пн-пт)"""
        from datetime import timedelta
        
        next_day = current_time + timedelta(days=1)
        
        # Если следующий день - суббота (5) или воскресенье (6), переходим к понедельнику
        while next_day.weekday() >= 5:  # 5=суббота, 6=воскресенье
            next_day += timedelta(days=1)
        
        return next_day
    
    def _find_next_custom_weekday(self, current_time: datetime, weekdays_str: str) -> datetime:
        """Найти следующий день из списка дней недели"""
        from datetime import timedelta
        
        # Парсим дни недели из строки (например, "1,3,5" для пн, ср, пт)
        try:
            weekdays = [int(d) for d in weekdays_str.split(',')]
        except (ValueError, AttributeError):
            logger.error(f"Неверный формат дней недели: {weekdays_str}")
            return None
        
        # Ищем следующий подходящий день
        next_day = current_time + timedelta(days=1)
        
        # Ищем в течение следующих 7 дней
        for _ in range(7):
            if next_day.weekday() in weekdays:
                return next_day
            next_day += timedelta(days=1)
        
        # Если не нашли в ближайшие 7 дней, что-то не так
        logger.error(f"Не удалось найти следующий день для дней недели: {weekdays_str}")
        return None
    
    def update_meeting(self, meeting_id: int, user_id: int, title: str = None, 
                      description: str = None, meeting_time: datetime = None,
                      is_recurring: bool = None, recurrence_type: str = None,
                      recurrence_interval: int = None, recurrence_weekdays: str = None,
                      recurrence_end_date: datetime = None) -> bool:
        """Обновление встречи (расширенная версия)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Проверяем, что встреча принадлежит пользователю
                cursor.execute('SELECT id FROM meetings WHERE id = ? AND user_id = ?', 
                             (meeting_id, user_id))
                if not cursor.fetchone():
                    return False
                
                # Строим запрос обновления
                updates = []
                params = []
                
                if title is not None:
                    updates.append("title = ?")
                    params.append(title)
                
                if description is not None:
                    updates.append("description = ?")
                    params.append(description)
                
                if meeting_time is not None:
                    updates.append("meeting_time = ?")
                    params.append(meeting_time)
                
                if is_recurring is not None:
                    updates.append("is_recurring = ?")
                    params.append(is_recurring)
                
                if recurrence_type is not None:
                    updates.append("recurrence_type = ?")
                    params.append(recurrence_type)
                
                if recurrence_interval is not None:
                    updates.append("recurrence_interval = ?")
                    params.append(recurrence_interval)
                
                if recurrence_weekdays is not None:
                    updates.append("recurrence_weekdays = ?")
                    params.append(recurrence_weekdays)
                
                if recurrence_end_date is not None:
                    updates.append("recurrence_end_date = ?")
                    params.append(recurrence_end_date)
                
                if not updates:
                    return True  # Нечего обновлять
                
                updates.append("updated_at = CURRENT_TIMESTAMP")
                params.extend([meeting_id, user_id])
                
                query = f'''
                    UPDATE meetings 
                    SET {', '.join(updates)}
                    WHERE id = ? AND user_id = ?
                '''
                
                cursor.execute(query, params)
                conn.commit()
                
                logger.info(f"Обновлена встреча ID {meeting_id} для пользователя {user_id}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Ошибка обновления встречи {meeting_id}: {e}")
            return False
