"""
Модуль для работы с уведомлениями в Telegram боте.
Включает функции проверки и отправки уведомлений по расписанию.
"""
import asyncio
import logging
import traceback
from datetime import datetime, timedelta
import pytz
import sys

# Импортируем необходимые функции из модуля base.db
from base.db import (
    MOSCOW_TZ, get_all_active_notifications,
    mark_notification_as_sent, fix_notification_timezone, 
    get_notifications_to_send
)

# Получаем логгер
logger = logging.getLogger(__name__)

# Установка уровня логирования для модуля
logger.setLevel(logging.DEBUG)

# Добавление обработчика для вывода в консоль
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Добавляем обработчик к логгеру, если его еще нет
if not logger.handlers:
    logger.addHandler(console_handler)
    
    # Добавляем также обработчик для записи в файл
    file_handler = logging.FileHandler('log/notifications.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

# Функция для проверки и отправки уведомлений
async def check_notifications(context):
    """
    Проверяет и отправляет уведомления, которые должны быть отправлены в данный момент
    
    Args:
        context: Контекст с доступом к боту для отправки сообщений
    """
    try:
        if not hasattr(context, 'bot') or not context.bot:
            return
            
        # Текущее время в МСК
        now = datetime.now(MOSCOW_TZ)
        
        # Получаем все активные уведомления для отправки
        try:
            notifications = get_notifications_to_send(now)
            if not notifications:
                return
                
        except Exception as e:
            return
        
        # Отправляем каждое уведомление
        for notification in notifications:
            notification_id, user_id, message = notification
            # Преобразуем значения из Decimal в int
            notification_id = int(notification_id)
            user_id = int(user_id)
            
            # Отправляем с повторными попытками
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    # Отправляем сообщение пользователю
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"🔔 Напоминание: {message}"
                    )                   
                    break  # Выходим из цикла попыток, если успешно
                except Exception as e:
                    error_traceback = traceback.format_exc()
                    if "bot was blocked by the user" in str(e).lower():
                        mark_notification_as_sent(notification_id)
                        break
                    
                    if attempt < max_retries:
                        wait_time = 2 * attempt  # Увеличиваем время ожидания с каждой попыткой
                        await asyncio.sleep(wait_time)
                    else:
                        pass
    except Exception as e:
        pass

# Функция для запуска проверки уведомлений в фоне
async def scheduled_job(context):
    iteration = 0
    
    try:
        # Сначала выполним немедленную проверку при запуске
        try:
            now = datetime.now(MOSCOW_TZ)
            await check_notifications(context)
        except Exception as e:
            pass
        
        # Затем начинаем регулярные проверки
        while True:
            iteration += 1
            try:
                # Ждем до начала следующей минуты
                now = datetime.now(MOSCOW_TZ)
                next_minute = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
                seconds_to_wait = (next_minute - now).total_seconds()
                
                # Спим до следующей минуты
                await asyncio.sleep(max(0, seconds_to_wait))
                
                # Проверяем уведомления
                await check_notifications(context)
            except Exception as e:
                await asyncio.sleep(15)
    except Exception as e:
        pass

# Функция для исправления часовых поясов уведомлений
async def fix_timezones(user_id=None):
    """
    Исправляет часовые пояса уведомлений.
    
    Args:
        user_id (int, optional): ID пользователя, чьи уведомления нужно исправить.
                                 Если None, исправляются все уведомления.
    
    Returns:
        int: Количество исправленных уведомлений
    """
    count = 0
    try:
        all_notifications = get_all_active_notifications()
        
        for notification_id, notif_user_id, _, notification_time, _ in all_notifications:
            # Пропускаем, если указан конкретный пользователь и это не его уведомление
            if user_id is not None and int(notif_user_id) != int(user_id):
                continue
                
            # Проверяем часовой пояс
            if notification_time.tzinfo is None or str(notification_time.tzinfo) != str(MOSCOW_TZ):
                # Если время не в московской зоне, конвертируем его
                if notification_time.tzinfo is None:
                    # Время без зоны - считаем, что оно в UTC
                    utc_time = notification_time.replace(tzinfo=pytz.UTC)
                    msk_time = utc_time.astimezone(MOSCOW_TZ)
                else:
                    # Время с другой зоной - конвертируем в московскую
                    msk_time = notification_time.astimezone(MOSCOW_TZ)
                
                # Обновляем время в базе
                if fix_notification_timezone(notification_id, msk_time):
                    count += 1
                else:
                    pass
    except Exception as e:
        pass
    
    return count 