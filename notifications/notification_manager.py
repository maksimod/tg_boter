import logging
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime

logger = logging.getLogger(__name__)

# Асинхронная внутренняя функция, которая будет использоваться внутри обертки
async def _create_notification_async(notification_datetime, notification_text, update=None, context=None):
    """
    Асинхронная функция для создания уведомления.
    
    Args:
        notification_datetime: Дата и время уведомления
        notification_text: Текст уведомления
        update: Объект Telegram update
        context: Объект Telegram context
        
    Returns:
        bool: True если уведомление успешно создано, False в противном случае
    """
    logger.debug(f"Creating notification: datetime={notification_datetime}, text={notification_text}")
    
    try:
        # Получаем ID пользователя для уведомления
        user_id = None
        chat_id = None
        
        if update:
            try:
                user_id = update.effective_user.id
                chat_id = update.effective_chat.id
                logger.debug(f"Got user_id={user_id}, chat_id={chat_id}")
            except Exception as e:
                logger.error(f"Error getting user_id: {e}", exc_info=True)
        
        # Если не удалось получить user_id, используем chat_id
        if not user_id and chat_id:
            logger.debug(f"Using chat_id={chat_id} as user_id")
            user_id = chat_id
            
        # Принудительное получение chat_id, если еще нет
        if not chat_id and context and update:
            chat_id = update.effective_chat.id
            logger.debug(f"Forcibly retrieved chat_id={chat_id}")
            if not user_id:
                user_id = chat_id
                logger.debug(f"Setting user_id={user_id} equal to chat_id")
        
        if not user_id:
            logger.error("Could not determine user_id or chat_id")
            if update and context:
                chat_id = update.effective_chat.id
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Ошибка: не удалось определить ID пользователя."
                )
                
                keyboard = [[InlineKeyboardButton("Вернуться в меню", callback_data="back_to_menu")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="Выберите действие:",
                    reply_markup=reply_markup
                )
            return False
            
        logger.info(f"Creating notification for user_id={user_id}, date={notification_datetime}, text={notification_text}")
        
        # Импортируем здесь, чтобы избежать циклических импортов
        from notifications.notification_parser import process_notification_request
        success = process_notification_request(notification_datetime, notification_text, update, context)
        
        if not success and update and context:
            # Если произошла ошибка и есть доступ к боту, отправляем сообщение
            chat_id = update.effective_chat.id
            await context.bot.send_message(
                chat_id=chat_id,
                text="Произошла ошибка при создании уведомления. Пожалуйста, проверьте формат даты и времени."
            )
            
            # Отправляем кнопку возврата в меню
            keyboard = [[InlineKeyboardButton("Вернуться в меню", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=chat_id,
                text="Выберите действие:",
                reply_markup=reply_markup
            )
            return False
            
        return success
    except Exception as e:
        logger.error(f"Error processing notification: {e}", exc_info=True)
        if update and context:
            chat_id = update.effective_chat.id
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Произошла ошибка при создании уведомления: {e}"
            )
            
            # Отправляем кнопку возврата в меню
            keyboard = [[InlineKeyboardButton("Вернуться в меню", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await context.bot.send_message(
                chat_id=chat_id,
                text="Выберите действие:",
                reply_markup=reply_markup
            )
            return False

# Обычная (не async) функция-обертка, которая запускает асинхронную функцию
def create_notification(notification_datetime, notification_text, update=None, context=None):
    """
    Создает уведомление на основе полученных данных.
    Эта функция является оберткой вокруг асинхронной функции _create_notification_async.
    
    Args:
        notification_datetime: Дата и время уведомления
        notification_text: Текст уведомления
        update: Объект Telegram update
        context: Объект Telegram context
        
    Returns:
        bool: True если уведомление успешно создано, False в противном случае
    """
    # Получаем текущий цикл событий или создаем новый
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # Если нет активного цикла событий, создаем новый
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Проверяем, запущен ли цикл событий
    if loop.is_running():
        # Если цикл событий запущен, создаем задачу
        logger.debug("Event loop is running, creating task")
        asyncio.create_task(_create_notification_async(notification_datetime, notification_text, update, context))
        return True
    else:
        # Если цикл событий не запущен, запускаем его
        logger.debug("Event loop is not running, running until complete")
        return loop.run_until_complete(_create_notification_async(notification_datetime, notification_text, update, context)) 