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

# Импортируем функции для работы с базой данных
from database import (
    MOSCOW_TZ, get_all_active_notifications, get_notifications_to_send,
    mark_notification_as_sent, fix_notification_timezone
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
    file_handler = logging.FileHandler('notifications.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

# Функция для проверки и отправки уведомлений
async def check_notifications(context):
    logger.debug("Начало проверки уведомлений")
    try:
        now = datetime.now(MOSCOW_TZ)
        logger.info(f"Проверка уведомлений в {now.strftime('%d.%m.%Y %H:%M:%S %z')}")
        
        # Проверяем доступность бота
        if not hasattr(context, 'bot'):
            logger.error("КРИТИЧЕСКАЯ ОШИБКА: context.bot не доступен - уведомления не могут быть отправлены")
            return
        else:
            logger.debug(f"Бот доступен: {context.bot}")
        
        # Выводим все активные уведомления для отладки
        all_notifications = get_all_active_notifications()
        logger.info(f"Всего активных уведомлений в базе: {len(all_notifications)}")
        
        if len(all_notifications) > 0:
            logger.debug("Список всех активных уведомлений:")
            for n in all_notifications:
                logger.debug(f"Активное уведомление: ID={n[0]}, user_id={n[1]}, text={n[2]}, time={n[3]}, is_sent={n[4]}")
        else:
            logger.debug("В базе нет активных уведомлений")
        
        # Получаем уведомления для отправки
        logger.debug(f"Получение уведомлений для отправки (текущее время: {now})")
        notifications = get_notifications_to_send(now)
        logger.info(f"Найдено {len(notifications)} уведомлений для отправки")
        
        if len(notifications) > 0:
            logger.debug("Список уведомлений для отправки:")
            for n in notifications:
                logger.debug(f"Будет отправлено: ID={n[0]}, user_id={n[1]}, text={n[2]}")
        
        for notification_id, user_id, message in notifications:
            try:
                # Преобразуем Decimal в int для отправки
                user_id_int = int(user_id)
                
                logger.debug(f"Попытка отправки уведомления {notification_id} пользователю {user_id_int}")
                logger.debug(f"Детали уведомления: ID={notification_id}, user_id={user_id_int}, text='{message}'")
                
                # Проверяем доступность bot в контексте еще раз для каждого уведомления
                if not hasattr(context, 'bot') or context.bot is None:
                    logger.error(f"Ошибка при отправке уведомления {notification_id}: context.bot не найден или равен None")
                    continue
                
                # Отправляем уведомление с дополнительной защитой от ошибок
                try:
                    logger.debug(f"Отправка сообщения через bot.send_message: chat_id={user_id_int}, text='{message}'")
                    await context.bot.send_message(
                        chat_id=user_id_int,
                        text=f"🔔 Напоминание: {message}"
                    )
                    logger.debug(f"Сообщение успешно отправлено пользователю {user_id_int}")
                except Exception as send_error:
                    error_traceback = traceback.format_exc()
                    logger.error(f"Ошибка при вызове send_message для уведомления {notification_id}: {send_error}")
                    logger.error(f"Трассировка ошибки при отправке: {error_traceback}")
                    continue
                
                # Помечаем уведомление как отправленное
                logger.debug(f"Пометка уведомления {notification_id} как отправленное")
                if mark_notification_as_sent(notification_id):
                    logger.info(f"Уведомление {notification_id} успешно отправлено пользователю {user_id} и помечено как отправленное")
                else:
                    logger.error(f"Не удалось пометить уведомление {notification_id} как отправленное, хотя сообщение было отправлено")
            except Exception as e:
                error_traceback = traceback.format_exc()
                logger.error(f"Ошибка при обработке уведомления {notification_id}: {e}")
                logger.error(f"Трассировка ошибки: {error_traceback}")
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Критическая ошибка в процессе проверки уведомлений: {e}")
        logger.error(f"Трассировка ошибки: {error_traceback}")
    finally:
        logger.debug("Завершение проверки уведомлений")

# Функция для запуска проверки уведомлений в фоне
async def scheduled_job(context):
    logger.info("Запуск планировщика уведомлений")
    iteration = 0
    
    try:
        while True:
            iteration += 1
            try:
                # Ждем до начала следующей минуты
                now = datetime.now(MOSCOW_TZ)
                next_minute = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
                seconds_to_wait = (next_minute - now).total_seconds()
                
                logger.info(f"Итерация #{iteration}: ожидание {seconds_to_wait:.2f} секунд до следующей проверки в {next_minute.strftime('%H:%M:%S')}")
                
                # Спим до следующей минуты
                await asyncio.sleep(max(0, seconds_to_wait))
                
                logger.debug(f"Итерация #{iteration}: пробуждение планировщика, начало проверки")
                # Проверяем уведомления
                await check_notifications(context)
                logger.debug(f"Итерация #{iteration}: завершение проверки")
            except Exception as e:
                error_traceback = traceback.format_exc()
                logger.error(f"Ошибка в планировщике на итерации #{iteration}: {e}")
                logger.error(f"Трассировка ошибки: {error_traceback}")
                # Продолжаем работу даже при ошибке
                logger.info("Планировщик продолжит работу через 60 секунд")
                await asyncio.sleep(60)
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Критическая ошибка в планировщике: {e}")
        logger.error(f"Трассировка ошибки: {error_traceback}")
        logger.error("Планировщик уведомлений остановлен!")

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
    logger.info(f"Запуск исправления часовых поясов для user_id={user_id if user_id else 'всех пользователей'}")
    count = 0
    try:
        all_notifications = get_all_active_notifications()
        logger.debug(f"Получено {len(all_notifications)} активных уведомлений для проверки часовых поясов")
        
        for notification_id, notif_user_id, _, notification_time, _ in all_notifications:
            # Пропускаем, если указан конкретный пользователь и это не его уведомление
            if user_id is not None and int(notif_user_id) != int(user_id):
                continue
                
            logger.debug(f"Проверка часового пояса для уведомления {notification_id} (пользователь {notif_user_id})")
            # Проверяем часовой пояс
            if notification_time.tzinfo is None or str(notification_time.tzinfo) != str(MOSCOW_TZ):
                # Если время не в московской зоне, конвертируем его
                if notification_time.tzinfo is None:
                    # Время без зоны - считаем, что оно в UTC
                    logger.debug(f"Уведомление {notification_id} не имеет часового пояса, преобразуем из UTC")
                    utc_time = notification_time.replace(tzinfo=pytz.UTC)
                    msk_time = utc_time.astimezone(MOSCOW_TZ)
                else:
                    # Время с другой зоной - конвертируем в московскую
                    logger.debug(f"Уведомление {notification_id} имеет неверный часовой пояс {notification_time.tzinfo}, преобразуем в МСК")
                    msk_time = notification_time.astimezone(MOSCOW_TZ)
                
                logger.debug(f"Обновление времени для уведомления {notification_id}: {notification_time} -> {msk_time}")
                # Обновляем время в базе
                if fix_notification_timezone(notification_id, msk_time):
                    count += 1
                    logger.info(f"Уведомление {notification_id} успешно обновлено на {msk_time}")
                else:
                    logger.error(f"Не удалось обновить часовой пояс для уведомления {notification_id}")
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Ошибка при исправлении часовых поясов: {e}")
        logger.error(f"Трассировка ошибки: {error_traceback}")
    
    logger.info(f"Завершение исправления часовых поясов. Исправлено {count} уведомлений")
    return count 