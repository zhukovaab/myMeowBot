"""Простая система ограничения частоты запросов"""

import time
from typing import Dict, Tuple

# Импортируем константу напрямую, чтобы избежать циклических импортов
MAX_MEETINGS_PER_DAY = 50

# Хранилище для отслеживания активности пользователей
# user_id -> (count, last_reset_time)
user_activity: Dict[int, Tuple[int, float]] = {}

def check_rate_limit(user_id: int, action: str = "meeting") -> Tuple[bool, int]:
    """
    Проверяет лимит действий для пользователя
    
    Args:
        user_id: ID пользователя
        action: Тип действия (пока только 'meeting')
    
    Returns:
        Tuple[bool, int]: (разрешено ли действие, оставшееся количество)
    """
    current_time = time.time()
    current_day = int(current_time // 86400)  # Секунды в дне
    
    if user_id not in user_activity:
        user_activity[user_id] = (0, current_day)
    
    count, last_day = user_activity[user_id]
    
    # Если прошел день, сбрасываем счетчик
    if current_day > last_day:
        count = 0
        last_day = current_day
    
    # Проверяем лимит
    if action == "meeting":
        limit = MAX_MEETINGS_PER_DAY
        if count >= limit:
            return False, 0
        
        # Увеличиваем счетчик
        count += 1
        user_activity[user_id] = (count, last_day)
        return True, limit - count
    
    return True, 0

def get_remaining_quota(user_id: int, action: str = "meeting") -> int:
    """Получить оставшуюся квоту для пользователя"""
    current_time = time.time()
    current_day = int(current_time // 86400)
    
    if user_id not in user_activity:
        return MAX_MEETINGS_PER_DAY
    
    count, last_day = user_activity[user_id]
    
    # Если прошел день, квота полная
    if current_day > last_day:
        return MAX_MEETINGS_PER_DAY
    
    if action == "meeting":
        return max(0, MAX_MEETINGS_PER_DAY - count)
    
    return 0

def cleanup_old_data():
    """Очистка старых данных (вызывается периодически)"""
    current_time = time.time()
    current_day = int(current_time // 86400)
    
    # Удаляем данные старше 2 дней
    to_remove = []
    for user_id, (count, last_day) in user_activity.items():
        if current_day - last_day > 2:
            to_remove.append(user_id)
    
    for user_id in to_remove:
        del user_activity[user_id]
