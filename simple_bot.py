#!/usr/bin/env python3
"""
Простой интерфейс для работы с системой уведомлений Telegram бота.
Позволяет легко интегрировать функцию создания уведомлений в другие приложения.

Основные функции:
- create_reminder - создать новое напоминание
- get_reminders - получить список активных напоминаний пользователя
- init_bot - инициализировать и запустить бота

Пример использования:
    from simple_bot import create_reminder, init_bot
    from datetime import datetime, timedelta
    import pytz
    
    # Инициализация бота при запуске приложения
    bot = init_bot()
    
    # Создание уведомления для пользователя 
    moscow_tz = pytz.timezone('Europe/Moscow')
    notification_time = moscow_tz.localize(datetime.now() + timedelta(minutes=5))
    create_reminder(user_id=123456789, notification_text="Не забудь позвонить маме!", notification_time=notification_time)
"""

import os
import logging
import time
import pytz
from datetime import datetime
from telegram.ext import Application

# Импортируем конфигурации
from credentials.telegram.config import BOT_TOKEN
from database import MOSCOW_TZ, init_database, create_notification, get_user_notifications
from notifications.core import setup_handlers, start_scheduler, start_bot_polling

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='simple_bot.log'
)
logger = logging.getLogger(__name__)

# Глобальный объект для доступа к боту
_bot_app = None

def init_bot(token=None, run=True):
    """
    Инициализирует и запускает Telegram бота
    
    Args:
        token (str, optional): Токен Telegram бота. Если не указан, берется из конфигурации.
        run (bool, optional): Если True, бот запускается автоматически. По умолчанию True.
    
    Returns:
        application: Объект приложения бота
    """
    global _bot_app
    
    if _bot_app is not None:
        return _bot_app
    
    # Используем токен из конфигурации, если не указан явно
    if token is None:
        token = BOT_TOKEN
    
    if not token:
        logger.error("Токен бота не найден!")
        return None
    
    # Инициализация базы данных
    logger.info("Инициализация базы данных для уведомлений...")
    init_database()
    
    # Создание приложения бота
    _bot_app = Application.builder().token(token).build()
    
    # Настройка обработчиков команд
    setup_handlers(_bot_app)
    
    # Запуск бота и планировщика в отдельных потоках
    if run:
        start_scheduler(_bot_app)
        start_bot_polling(_bot_app)
        logger.info("Бот и планировщик уведомлений успешно запущены")
    
    return _bot_app

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
        
        # Логируем создание
        logger.info(f"Создано напоминание для {user_id} на {notification_time}: {notification_text}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при создании напоминания: {e}")
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
        logger.error(f"Ошибка при получении напоминаний: {e}")
        return []

# Основная функция для запуска бота напрямую
def main():
    """
    Функция для запуска бота напрямую
    """
    init_bot()
    
    # Ожидаем ввод от пользователя для завершения
    print("Бот запущен! Нажмите Ctrl+C для остановки...")
    
    try:
        # Бесконечный цикл чтобы бот продолжал работать
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Бот остановлен!")

if __name__ == "__main__":
    main() 