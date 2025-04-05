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

# Импортируем необходимые функции из модуля database
from database import (
    MOSCOW_TZ, get_all_active_notifications,
    mark_notification_as_sent, fix_notification_timezone, 
    NOTIFICATIONS_TABLE, get_db_connection, get_notifications_to_send
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
            logger.error("Объект бота недоступен в контексте для отправки уведомлений")
            return
            
        # Текущее время в МСК
        now = datetime.now(MOSCOW_TZ)
        logger.debug(f"Проверка уведомлений в {now.strftime('%d.%m.%Y %H:%M:%S.%f %z')}")
        
        # Получаем все активные уведомления для отправки
        try:
            notifications = get_notifications_to_send(now)
            logger.info(f"Найдено {len(notifications)} уведомлений для отправки")
            
            if not notifications:
                logger.debug("Нет уведомлений для отправки")
                return
                
            logger.debug(f"Уведомления для отправки: {notifications}")
        except Exception as e:
            logger.error(f"Ошибка при получении уведомлений из БД: {e}")
            logger.error(traceback.format_exc())
            return
        
        # Отправляем каждое уведомление
        for notification in notifications:
            notification_id, user_id, message = notification
            # Преобразуем значения из Decimal в int
            notification_id = int(notification_id)
            user_id = int(user_id)
            
            logger.info(f"Отправка уведомления #{notification_id} пользователю {user_id}: {message}")
            
            # Отправляем с повторными попытками
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    # Отправляем сообщение пользователю
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"🔔 Напоминание: {message}"
                    )
                    logger.info(f"Уведомление #{notification_id} успешно отправлено пользователю {user_id}")
                    
                    # Помечаем уведомление как отправленное
                    if mark_notification_as_sent(notification_id):
                        logger.info(f"Уведомление #{notification_id} помечено как отправленное")
                    else:
                        logger.error(f"Ошибка при обновлении статуса уведомления #{notification_id}")
                    
                    break  # Выходим из цикла попыток, если успешно
                except Exception as e:
                    error_traceback = traceback.format_exc()
                    logger.error(f"Попытка {attempt}/{max_retries} - Ошибка при отправке уведомления #{notification_id} пользователю {user_id}: {e}")
                    if "bot was blocked by the user" in str(e).lower():
                        logger.warning(f"Бот заблокирован пользователем {user_id}, пометка уведомления как отправленное")
                        mark_notification_as_sent(notification_id)
                        break
                    
                    if attempt < max_retries:
                        wait_time = 2 * attempt  # Увеличиваем время ожидания с каждой попыткой
                        logger.info(f"Повторная попытка через {wait_time} секунд...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"Не удалось отправить уведомление #{notification_id} после {max_retries} попыток")
                        logger.error(f"Трассировка ошибки: {error_traceback}")
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Критическая ошибка в функции проверки уведомлений: {e}")
        logger.error(f"Трассировка ошибки: {error_traceback}")

# Функция для запуска проверки уведомлений в фоне
async def scheduled_job(context):
    logger.info("Запуск планировщика уведомлений")
    iteration = 0
    
    try:
        # Сначала выполним немедленную проверку при запуске
        logger.info("Выполнение немедленной проверки при запуске планировщика...")
        try:
            now = datetime.now(MOSCOW_TZ)
            logger.info(f"Текущее время: {now.strftime('%d.%m.%Y %H:%M:%S.%f %z')}")
            logger.info("Проверка пропущенных уведомлений...")
            await check_notifications(context)
            logger.info("Немедленная проверка завершена")
        except Exception as e:
            logger.error(f"Ошибка при немедленной проверке: {e}")
            logger.error(traceback.format_exc())
        
        # Затем начинаем регулярные проверки
        while True:
            iteration += 1
            try:
                # Ждем до начала следующей минуты
                now = datetime.now(MOSCOW_TZ)
                next_minute = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
                seconds_to_wait = (next_minute - now).total_seconds()
                
                logger.info(f"Итерация #{iteration}: ожидание {seconds_to_wait:.2f} секунд до начала следующей минуты ({next_minute.strftime('%H:%M:00')})")
                
                # Спим до следующей минуты
                await asyncio.sleep(max(0, seconds_to_wait))
                
                # Проверяем момент обработки (должен быть ровно в начале минуты)
                check_time = datetime.now(MOSCOW_TZ)
                logger.info(f"Итерация #{iteration}: обработка началась в {check_time.strftime('%H:%M:%S.%f')} (запланировано на {next_minute.strftime('%H:%M:%S')})")
                
                # Проверяем уведомления
                await check_notifications(context)
                
                # Логируем время завершения
                end_time = datetime.now(MOSCOW_TZ)
                logger.info(f"Итерация #{iteration}: обработка завершена в {end_time.strftime('%H:%M:%S.%f')}, заняла {(end_time - check_time).total_seconds():.3f} сек")
                
                # Если проверка заняла больше 45 секунд, логируем предупреждение о возможных пропущенных проверках
                if (end_time - check_time).total_seconds() > 45:
                    logger.warning(f"Проверка заняла более 45 секунд! Возможно, следующие уведомления будут пропущены.")
            except Exception as e:
                error_traceback = traceback.format_exc()
                logger.error(f"Ошибка в планировщике на итерации #{iteration}: {e}")
                logger.error(f"Трассировка ошибки: {error_traceback}")
                # Продолжаем работу даже при ошибке
                logger.info("Планировщик продолжит работу через 15 секунд")
                await asyncio.sleep(15)
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