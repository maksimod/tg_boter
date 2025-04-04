"""
Interface for creating and managing reminders
"""
import logging
import traceback
import pytz
from datetime import datetime

from database import MOSCOW_TZ, create_notification, get_user_notifications

# Получаем логгер
logger = logging.getLogger(__name__)

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
        logger.info(f"Создание напоминания для пользователя {user_id} на {notification_time}")
        
        # Проверка часового пояса
        if notification_time.tzinfo is None:
            # Если время без зоны, считаем что оно в московской зоне
            logger.debug(f"Время {notification_time} не имеет часового пояса, применяем МСК")
            notification_time = MOSCOW_TZ.localize(notification_time)
        elif str(notification_time.tzinfo) != str(MOSCOW_TZ):
            # Если в другой зоне, конвертируем в московскую
            logger.debug(f"Время {notification_time} в часовом поясе {notification_time.tzinfo}, конвертируем в МСК")
            notification_time = notification_time.astimezone(MOSCOW_TZ)
        
        # Создаем уведомление в базе данных
        logger.debug(f"Сохранение уведомления в базу данных: {user_id}, '{notification_text}', {notification_time}")
        create_notification(user_id, notification_text, notification_time)
        
        # Логируем создание
        logger.info(f"Успешно создано напоминание для {user_id} на {notification_time}: {notification_text}")
        return True
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Ошибка при создании напоминания: {e}")
        logger.error(f"Трассировка ошибки: {error_traceback}")
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
        logger.info(f"Получение активных напоминаний для пользователя {user_id}")
        reminders = get_user_notifications(user_id)
        logger.info(f"Найдено {len(reminders)} активных напоминаний для пользователя {user_id}")
        return reminders
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Ошибка при получении напоминаний: {e}")
        logger.error(f"Трассировка ошибки: {error_traceback}")
        return [] 