"""
Модуль для парсинга и обработки данных уведомлений
"""
import logging
import traceback
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import asyncio

from notifications.reminders import create_reminder
from database import MOSCOW_TZ

# Настройка логгера
logger = logging.getLogger(__name__)

def parse_notification_datetime(notification_datetime_str):
    """
    Парсит строку даты и времени в формате ДД.ММ.ГГ ЧЧ:ММ
    
    Args:
        notification_datetime_str (str): Строка с датой и временем в формате ДД.ММ.ГГ ЧЧ:ММ
        
    Returns:
        datetime: Объект datetime или None, если произошла ошибка
    """
    try:
        # Преобразуем строку даты и времени в объект datetime
        dt_parts = notification_datetime_str.split(' ')
        date_parts = dt_parts[0].split('.')
        time_parts = dt_parts[1].split(':')
        
        day = int(date_parts[0])
        month = int(date_parts[1])
        year = int('20' + date_parts[2]) if len(date_parts[2]) == 2 else int(date_parts[2])
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        
        notification_time = datetime(year, month, day, hour, minute)
        
        # Добавляем московскую зону
        notification_time = MOSCOW_TZ.localize(notification_time)
        
        return notification_time
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка при парсинге даты и времени '{notification_datetime_str}': {e}")
        return None

def process_notification_request(notification_datetime, notification_text, current_update=None, current_context=None):
    """
    Обрабатывает запрос на создание уведомления
    
    Args:
        notification_datetime (str): Дата и время в формате ДД.ММ.ГГ ЧЧ:ММ
        notification_text (str): Текст уведомления
        current_update: Объект Update из Telegram (опционально)
        current_context: Объект Context из Telegram (опционально)
        
    Returns:
        bool: True если уведомление успешно создано, False в противном случае
    """
    try:
        logger.info(f"Обработка запроса на создание уведомления: {notification_datetime}, {notification_text}")
        
        # Поддержка для старых вызовов с current_update и current_context
        if current_update and current_context:
            logger.debug("Обработка с использованием объектов update и context")
            try:
                chat_id = current_update.effective_chat.id
                user_id = current_update.effective_user.id
                logger.info(f"Получены chat_id={chat_id}, user_id={user_id}")
            except Exception as e:
                logger.error(f"Ошибка при получении ID: {e}")
                # Устанавливаем chat_id и user_id по умолчанию
                chat_id = getattr(current_update, 'effective_chat', None)
                if chat_id:
                    chat_id = getattr(chat_id, 'id', None)
                
                user_id = getattr(current_update, 'effective_user', None)
                if user_id:
                    user_id = getattr(user_id, 'id', None)
                
                logger.info(f"Получены альтернативные chat_id={chat_id}, user_id={user_id}")
                
                if not user_id and chat_id:
                    user_id = chat_id
                    logger.info(f"Используем chat_id в качестве user_id: {user_id}")
            
            # Парсим дату и время
            notification_time = parse_notification_datetime(notification_datetime)
            if not notification_time:
                logger.error(f"Некорректный формат даты и времени: {notification_datetime}")
                if chat_id:
                    asyncio.create_task(current_context.bot.send_message(
                        chat_id=chat_id,
                        text=f"Некорректный формат даты и времени. Используйте формат ДД.ММ.ГГ ЧЧ:ММ, например 31.03.25 16:17."
                    ))
                return False
            
            # Проверяем, что дата не в прошлом
            current_time = datetime.now(MOSCOW_TZ)
            if notification_time < current_time:
                logger.error(f"Попытка создать уведомление на прошедшую дату: {notification_datetime}")
                if chat_id:
                    asyncio.create_task(current_context.bot.send_message(
                        chat_id=chat_id,
                        text="Невозможно создать уведомление на прошедшую дату и время."
                    ))
                return False
            
            # Вычисляем разницу во времени для отображения
            time_diff = notification_time - current_time
            minutes_diff = int(time_diff.total_seconds() / 60)
            
            # Проверка user_id перед созданием уведомления
            if not user_id:
                logger.error("Не удалось получить user_id для создания уведомления")
                if chat_id:
                    asyncio.create_task(current_context.bot.send_message(
                        chat_id=chat_id,
                        text="Ошибка: не удалось определить ID пользователя для создания уведомления."
                    ))
                return False
            
            # Создаем уведомление в базе данных
            logger.info(f"Создание уведомления для user_id={user_id}, время={notification_time}, текст={notification_text}")
            success = create_reminder(user_id, notification_text, notification_time)
            
            if success:
                logger.info(f"Уведомление успешно создано для user_id={user_id}")
                # Формируем сообщение с деталями уведомления
                message = (
                    f"Уведомление создано!\n\n"
                    f"Текст: {notification_text}\n"
                    f"Дата и время: {notification_datetime}\n"
                    f"(Будет отправлено через {minutes_diff} мин.)"
                )
                
                # Отправляем подтверждение
                if chat_id:
                    asyncio.create_task(current_context.bot.send_message(
                        chat_id=chat_id,
                        text=message
                    ))
                
                    # Отправляем кнопку возврата в меню
                    keyboard = [[InlineKeyboardButton("Вернуться в меню", callback_data="back_to_menu")]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    asyncio.create_task(current_context.bot.send_message(
                        chat_id=chat_id,
                        text="Выберите действие:",
                        reply_markup=reply_markup
                    ))
                
                return True
            else:
                logger.error(f"Не удалось создать уведомление для user_id={user_id}")
                if chat_id:
                    asyncio.create_task(current_context.bot.send_message(
                        chat_id=chat_id,
                        text="Произошла ошибка при создании уведомления. Пожалуйста, попробуйте еще раз позже."
                    ))
                return False
                
        else:
            # Прямое создание уведомления без контекста Telegram
            logger.debug("Обработка без объектов update и context")
            
            # Получаем user_id из контекста если он доступен, иначе берем из easy_bot
            user_id = None
            chat_id = None
            
            # Импортируем current_update только здесь, чтобы избежать циклических импортов
            try:
                from easy_bot import current_update
                logger.debug("Импортирован модуль easy_bot")
                if current_update:
                    try:
                        user_id = current_update.effective_user.id
                        chat_id = current_update.effective_chat.id
                        logger.info(f"Из easy_bot получены user_id={user_id}, chat_id={chat_id}")
                    except Exception as e:
                        logger.error(f"Ошибка при получении ID из easy_bot: {e}")
            except Exception as import_error:
                logger.error(f"Ошибка при импорте easy_bot: {import_error}")
            
            if not user_id and chat_id:
                logger.warning(f"Не удалось получить ID пользователя, используем ID чата: {chat_id}")
                user_id = chat_id
                
            if not user_id:
                logger.error("Не удалось получить ID пользователя или чата")
                return False
            
            # Парсим дату и время
            notification_time = parse_notification_datetime(notification_datetime)
            if not notification_time:
                logger.error(f"Некорректный формат даты и времени: {notification_datetime}")
                return False
            
            # Проверяем, что дата не в прошлом
            current_time = datetime.now(MOSCOW_TZ)
            if notification_time < current_time:
                logger.error(f"Попытка создать уведомление на прошедшую дату: {notification_datetime}")
                return False
            
            # Создаем уведомление в базе данных
            logger.info(f"Создание уведомления для user_id={user_id}, время={notification_time}, текст={notification_text}")
            success = create_reminder(user_id, notification_text, notification_time)
            
            if success:
                logger.info(f"Уведомление успешно создано для user_id={user_id}")
                return True
            else:
                logger.error(f"Ошибка при создании уведомления для пользователя {user_id}")
                return False
            
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Ошибка при обработке запроса на создание уведомления: {e}")
        logger.error(f"Трассировка ошибки: {error_traceback}")
        
        if current_update and current_context:
            try:
                chat_id = current_update.effective_chat.id
                asyncio.create_task(current_context.bot.send_message(
                    chat_id=chat_id,
                    text=f"Произошла ошибка при создании уведомления: {e}"
                ))
            except Exception as msg_error:
                logger.error(f"Не удалось отправить сообщение об ошибке: {msg_error}")
        
        return False 