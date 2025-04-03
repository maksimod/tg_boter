"""
Модуль для работы с уведомлениями в Telegram боте.
Включает функции проверки и отправки уведомлений по расписанию.
"""
import asyncio
import logging
from datetime import datetime, timedelta
import pytz

# Импортируем функции для работы с базой данных
from database import (
    MOSCOW_TZ, get_all_active_notifications, get_notifications_to_send,
    mark_notification_as_sent, fix_notification_timezone
)

# Получаем логгер
logger = logging.getLogger(__name__)

# Функция для проверки и отправки уведомлений
async def check_notifications(context):
    now = datetime.now(MOSCOW_TZ)
    logger.info(f"Проверка уведомлений в {now.strftime('%d.%m.%Y %H:%M:%S %z')}")
    
    # Выводим все активные уведомления для отладки
    all_notifications = get_all_active_notifications()
    logger.info(f"Всего активных уведомлений в базе: {len(all_notifications)}")
    for n in all_notifications:
        logger.info(f"Активное уведомление: ID={n[0]}, user_id={n[1]}, text={n[2]}, time={n[3]}, is_sent={n[4]}")
    
    # Получаем уведомления для отправки
    notifications = get_notifications_to_send(now)
    logger.info(f"Найдено {len(notifications)} уведомлений для отправки")
    
    for notification_id, user_id, notification_text in notifications:
        try:
            # Преобразуем Decimal в int для отправки
            user_id_int = int(user_id)
            
            # Отправляем уведомление
            await context.bot.send_message(
                chat_id=user_id_int,
                text=f"🔔 Напоминание: {notification_text}"
            )
            
            # Помечаем уведомление как отправленное
            mark_notification_as_sent(notification_id)
            logger.info(f"Уведомление {notification_id} отправлено пользователю {user_id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления {notification_id}: {e}")

# Функция для запуска проверки уведомлений в фоне
async def scheduled_job(context):
    while True:
        try:
            # Ждем до начала следующей минуты
            now = datetime.now(MOSCOW_TZ)
            next_minute = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
            seconds_to_wait = (next_minute - now).total_seconds()
            
            logger.info(f"Ожидание {seconds_to_wait:.2f} секунд до следующей проверки в {next_minute.strftime('%H:%M:%S')}")
            
            # Спим до следующей минуты
            await asyncio.sleep(max(0, seconds_to_wait))
            
            # Проверяем уведомления
            await check_notifications(context)
        except Exception as e:
            logger.error(f"Ошибка в планировщике: {e}")
            # Продолжаем работу даже при ошибке
            await asyncio.sleep(60)

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
    
    return count 