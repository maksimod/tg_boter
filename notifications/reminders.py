"""
Interface for creating and managing reminders
"""
import traceback
import pytz
from datetime import datetime

from base.db import MOSCOW_TZ, create_notification, get_user_notifications

def create_reminder(user_id, notification_text, notification_time):
    """
    Создает новое напоминание в базе данных
    
    Args:
        user_id (int): ID пользователя Telegram
        notification_text (str): Текст уведомления
        notification_time (datetime): Время отправки уведомления (с учетом часового пояса)
    
    Returns:
        bool: True если успешно, False если произошла ошибка
    """
    try:
        # Проверка часового пояса
        if notification_time.tzinfo is None:
            # Если время без зоны, считаем что оно в московской зоне
            notification_time = MOSCOW_TZ.localize(notification_time)
        elif str(notification_time.tzinfo) != str(MOSCOW_TZ):
            # Если в другой зоне, конвертируем в московскую
            notification_time = notification_time.astimezone(MOSCOW_TZ)
        
        # Создаем уведомление в базе данных
        create_notification(user_id, notification_text, notification_time)
        
        return True
    except Exception as e:
        error_traceback = traceback.format_exc()
        return False

def get_reminders(user_id):
    """
    Получает список активных напоминаний пользователя
    
    Args:
        user_id (int): ID пользователя Telegram
    
    Returns:
        list: Список активных напоминаний
    """
    try:
        reminders = get_user_notifications(user_id)
        return reminders
    except Exception as e:
        error_traceback = traceback.format_exc()
        return [] 