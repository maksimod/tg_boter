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
import sys
import traceback
from datetime import datetime
from telegram.ext import Application

# Импортируем конфигурации
from credentials.telegram.config import BOT_TOKEN
from database import MOSCOW_TZ, init_database, create_notification, get_user_notifications
from notifications.core import setup_handlers, start_scheduler, start_bot_polling

# Настройка логирования
def setup_logging():
    """Настраивает логирование для всего приложения"""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Форматирование логов
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Обработчик для вывода в файл
    file_handler = logging.FileHandler('simple_bot.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Обработчик для вывода в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    
    # Добавляем обработчики к корневому логгеру
    if not root_logger.handlers:
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
    
    # Логируем запуск логирования
    root_logger.info("Логирование настроено")
    return root_logger

# Настраиваем логирование при импорте модуля
logger = setup_logging()

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
    
    logger.info("Инициализация бота")
    
    if _bot_app is not None:
        logger.info("Бот уже инициализирован, возвращаем существующий экземпляр")
        return _bot_app
    
    # Используем токен из конфигурации, если не указан явно
    if token is None:
        token = BOT_TOKEN
    
    if not token:
        logger.error("Токен бота не найден!")
        return None
    
    try:
        # Инициализация базы данных
        logger.info("Инициализация базы данных для уведомлений...")
        init_database()
        
        # Создание приложения бота
        logger.info("Создание приложения бота с токеном")
        _bot_app = Application.builder().token(token).build()
        
        # Настройка обработчиков команд
        logger.info("Настройка обработчиков команд бота")
        setup_handlers(_bot_app)
        
        # Запуск бота и планировщика в отдельных потоках
        if run:
            logger.info("Запуск бота и планировщика уведомлений")
            scheduler_thread = start_scheduler(_bot_app)
            bot_thread = start_bot_polling(_bot_app)
            logger.info("Бот и планировщик уведомлений успешно запущены")
            logger.info(f"ID потока планировщика: {scheduler_thread.ident}, ID потока бота: {bot_thread.ident}")
        
        return _bot_app
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Ошибка при инициализации бота: {e}")
        logger.error(f"Трассировка ошибки: {error_traceback}")
        return None

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

# Основная функция для запуска бота напрямую
def main():
    """
    Функция для запуска бота напрямую
    """
    logger.info("Запуск бота напрямую через функцию main()")
    bot = init_bot()
    
    if not bot:
        logger.error("Не удалось инициализировать бота, завершение работы")
        return
    
    # Ожидаем ввод от пользователя для завершения
    print("Бот запущен! Нажмите Ctrl+C для остановки...")
    logger.info("Бот запущен и ожидает сообщений")
    
    try:
        # Бесконечный цикл чтобы бот продолжал работать
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Получен сигнал KeyboardInterrupt, завершение работы")
        print("Бот остановлен!")

if __name__ == "__main__":
    main() 