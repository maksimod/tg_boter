import logging
import asyncio
from typing import List, Union, Optional
import asyncpg

# Import necessary modules
from easy_bot import get_bot_instance, current_update, get_chat_id_from_update

logger = logging.getLogger(__name__)

async def get_all_user_chat_ids() -> List[int]:
    """
    Получает все chat_id пользователей из базы данных PostgreSQL.
    
    Returns:
        List[int]: Список chat_id всех пользователей
    """
    conn = None
    try:
        # Загружаем настройки PostgreSQL напрямую
        from credentials.postgres.config import HOST, PORT, DATABASE, USER, PASSWORD, BOT_PREFIX
        logger.info(f"Подключение к PostgreSQL: {HOST}:{PORT}, БД: {DATABASE}, пользователь: {USER}")
        
        # Устанавливаем прямое соединение с PostgreSQL
        conn = await asyncpg.connect(
            host=HOST,
            port=PORT,
            user=USER,
            password=PASSWORD,
            database=DATABASE,
            timeout=10.0
        )
        
        # Проверяем соединение
        await conn.fetchval("SELECT 1")
        logger.info("Соединение с PostgreSQL успешно установлено")
        
        # Получаем список пользователей
        query = f"SELECT DISTINCT chat_id FROM {BOT_PREFIX}users"
        rows = await conn.fetch(query)
        
        # Извлекаем chat_id из результата
        chat_ids = [row['chat_id'] for row in rows]
        logger.info(f"Получено {len(chat_ids)} chat_id пользователей из PostgreSQL")
        
        # Если не найдено пользователей, добавим тестового пользователя
        if not chat_ids:
            logger.warning("Не найдено пользователей в базе данных PostgreSQL. Добавляем тестового пользователя.")
            
            # Добавляем тестового пользователя
            current_update_obj = current_update
            if current_update_obj and hasattr(current_update_obj, 'effective_user'):
                user_id = current_update_obj.effective_user.id
                chat_id = get_chat_id_from_update(current_update_obj)
                username = current_update_obj.effective_user.username or "test_user"
                
                logger.info(f"Добавление текущего пользователя в БД: user_id={user_id}, chat_id={chat_id}, username={username}")
                
                await conn.execute(
                    f"INSERT INTO {BOT_PREFIX}users (user_id, chat_id, username) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET chat_id = $2, username = $3",
                    user_id, chat_id, username
                )
                
                # Получаем обновленный список пользователей
                rows = await conn.fetch(query)
                chat_ids = [row['chat_id'] for row in rows]
                logger.info(f"После добавления получено {len(chat_ids)} chat_id пользователей")
            else:
                logger.error("Не удалось получить информацию о текущем пользователе для добавления тестового пользователя")
                
                # Используем тестовые данные
                test_user_id = 123456789
                test_chat_id = 123456789
                test_username = "test_user"
                
                logger.info(f"Добавление тестового пользователя в БД: user_id={test_user_id}, chat_id={test_chat_id}, username={test_username}")
                
                await conn.execute(
                    f"INSERT INTO {BOT_PREFIX}users (user_id, chat_id, username) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET chat_id = $2, username = $3",
                    test_user_id, test_chat_id, test_username
                )
                
                # Получаем обновленный список пользователей
                rows = await conn.fetch(query)
                chat_ids = [row['chat_id'] for row in rows]
                logger.info(f"После добавления получено {len(chat_ids)} chat_id пользователей")
        
        return chat_ids
    except Exception as e:
        logger.error(f"Ошибка при получении chat_id пользователей из PostgreSQL: {e}")
        # Возвращаем пустой список вместо выброса исключения
        return []
    finally:
        if conn:
            await conn.close()

async def send_message_to_chat(chat_id: int, message: str) -> bool:
    """
    Отправляет сообщение конкретному пользователю по chat_id.
    
    Args:
        chat_id: ID чата для отправки сообщения
        message: Текст сообщения
        
    Returns:
        bool: True, если сообщение успешно отправлено
    """
    # Получаем экземпляр приложения
    app = get_bot_instance()
    if app is None:
        logger.error("Экземпляр бота не найден")
        raise RuntimeError("Экземпляр бота не найден")
    
    # Отправляем сообщение с помощью bot, а не application
    await app.bot.send_message(chat_id=chat_id, text=message)
    logger.info(f"Сообщение отправлено пользователю с chat_id {chat_id}")
    return True

async def announce(message: str, chat_ids: Union[List[int], str, None] = None) -> bool:
    """
    Отправляет объявление всем пользователям бота или указанному списку чатов.
    
    Args:
        message (str): Текст объявления
        chat_ids (Union[List[int], str, None]): Список chat_id для отправки или строка 'all' для всех пользователей
        
    Returns:
        bool: True если объявление успешно отправлено хотя бы одному пользователю, иначе False
    """
    # Получаем инстанс бота
    bot_app = get_bot_instance()
    if not bot_app:
        logger.error("Бот не инициализирован, невозможно отправить объявление")
        return False
    
    # Определяем получателей
    recipient_chat_ids = []
    
    # Если chat_ids это строка 'all' или None, получаем всех пользователей из базы
    if chat_ids == "all" or chat_ids is None:
        try:
            recipient_chat_ids = await get_all_user_chat_ids()
            
            # Если пользователей не найдено, но у нас есть текущий пользователь
            if not recipient_chat_ids and current_update:
                current_chat_id = get_chat_id_from_update(current_update)
                if current_chat_id:
                    logger.warning(f"В базе данных нет пользователей, отправляем только текущему пользователю: {current_chat_id}")
                    recipient_chat_ids = [current_chat_id]
                    
        except Exception as e:
            logger.error(f"Ошибка при получении chat_id пользователей: {e}")
            # В случае ошибки, пробуем отправить сообщение текущему пользователю
            if current_update:
                current_chat_id = get_chat_id_from_update(current_update)
                if current_chat_id:
                    logger.info(f"Отправляем объявление только текущему пользователю: {current_chat_id}")
                    recipient_chat_ids = [current_chat_id]
    else:
        # Используем переданный список chat_ids
        if isinstance(chat_ids, list):
            recipient_chat_ids = chat_ids
        else:
            # Если передан одиночный chat_id, преобразуем его в список
            recipient_chat_ids = [int(chat_ids)]
    
    # Проверяем, что есть кому отправлять
    if not recipient_chat_ids:
        logger.error("Не указаны получатели для отправки объявления")
        return False
    
    # Отправляем объявление
    success_count = 0
    total_count = len(recipient_chat_ids)
    
    for chat_id in recipient_chat_ids:
        try:
            await bot_app.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="HTML"
            )
            logger.info(f"Объявление успешно отправлено пользователю {chat_id}")
            success_count += 1
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения пользователю {chat_id}: {e}")
    
    # Логируем результаты
    logger.info(f"Объявление отправлено {success_count} из {total_count} пользователям")
    
    # Если хотя бы одно сообщение доставлено, считаем успехом
    if success_count > 0:
        return True
    else:
        logger.error(f"Не удалось отправить ни одного сообщения")
        return False 