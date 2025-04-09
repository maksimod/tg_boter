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

async def announce(message: str, recipients: Union[List[int], str]) -> bool:
    """
    Отправляет объявление указанным получателям.
    
    Args:
        message: Текст сообщения
        recipients: Список chat_id пользователей или строка "all" для отправки всем
        
    Returns:
        bool: True, если сообщения успешно отправлены
    """
    if not message:
        logger.error("Пустое сообщение")
        return False
    
    # Определяем получателей
    chat_ids = []
    if recipients == "all":
        # Получаем пользователей из базы данных PostgreSQL
        chat_ids = await get_all_user_chat_ids()
        if not chat_ids:
            logger.error("Не найдено пользователей в базе данных PostgreSQL")
            return False
        logger.info(f"Отправка объявления всем ({len(chat_ids)}) пользователям")
    elif isinstance(recipients, list):
        if not recipients:
            logger.error("Пустой список получателей")
            return False
        chat_ids = recipients
        logger.info(f"Отправка объявления {len(chat_ids)} указанным пользователям")
    elif isinstance(recipients, (int, str)) and str(recipients).isdigit():
        # Обработка одного ID пользователя
        chat_ids = [int(recipients)]
        logger.info(f"Отправка объявления одному пользователю с ID {recipients}")
    else:
        logger.error(f"Неверный формат получателей: {recipients}")
        return False
    
    # Убираем дубликаты
    chat_ids = list(set(chat_ids))
    logger.info(f"Итоговый список получателей: {chat_ids}")
    
    # Отправляем сообщение всем получателям
    success_count = 0
    for chat_id in chat_ids:
        try:
            await send_message_to_chat(chat_id, message)
            success_count += 1
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения пользователю {chat_id}: {e}")
    
    success_rate = success_count / len(chat_ids) if chat_ids else 0
    if success_rate < 0.5:  # Если больше половины отправок не удались
        logger.error(f"Менее половины сообщений доставлено: {success_count} из {len(chat_ids)}")
        return False
    
    return True 