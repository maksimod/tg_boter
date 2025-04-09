import logging
import asyncio
from typing import List, Union, Optional

# Import necessary modules
from easy_bot import get_bot_instance, current_update, get_chat_id_from_update

logger = logging.getLogger(__name__)

async def get_all_user_chat_ids() -> List[int]:
    """
    Получает все chat_id пользователей из базы данных.
    
    Returns:
        List[int]: Список chat_id всех пользователей
    """
    try:
        # Проверяем, какая база данных используется
        try:
            from credentials.postgres.config import USE_SQLITE, SQLITE_DB_PATH
            using_sqlite = USE_SQLITE
            sqlite_path = SQLITE_DB_PATH
        except (ImportError, AttributeError):
            using_sqlite = False
            sqlite_path = "db/local_database.db"
            
        logger.info(f"База данных: {'SQLite' if using_sqlite else 'PostgreSQL'}, путь: {sqlite_path if using_sqlite else 'PostgreSQL'}")
        
        if using_sqlite:
            # Используем SQLite
            import sqlite3
            import os
            
            # Проверяем существование файла БД
            if not os.path.exists(sqlite_path):
                logger.error(f"Файл базы данных SQLite не найден: {sqlite_path}")
                return []
                
            # Подключаемся к SQLite
            connection = sqlite3.connect(sqlite_path)
            cursor = connection.cursor()
            
            # Импортируем префикс таблицы
            try:
                from credentials.postgres.config import BOT_PREFIX
            except (ImportError, AttributeError):
                BOT_PREFIX = "tgbot_"
                
            try:
                # Проверяем существование таблицы пользователей
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{BOT_PREFIX}users'")
                if not cursor.fetchone():
                    logger.error(f"Таблица {BOT_PREFIX}users не найдена в SQLite")
                    return []
                    
                # Получаем chat_id пользователей
                cursor.execute(f"SELECT DISTINCT chat_id FROM {BOT_PREFIX}users")
                chat_ids = [row[0] for row in cursor.fetchall()]
                logger.info(f"Получено {len(chat_ids)} chat_id пользователей из SQLite")
                return chat_ids
            except Exception as e:
                logger.error(f"Ошибка при работе с SQLite: {e}")
                return []
            finally:
                connection.close()
        else:
            # Используем PostgreSQL
            from easy_bot import get_db_connection, BOT_PREFIX
            
            # Получаем соединение с базой данных
            conn = await get_db_connection()
            if conn is None:
                logger.error("Не удалось подключиться к базе данных PostgreSQL")
                return []
            
            try:
                # PostgreSQL запрос
                query = f"SELECT DISTINCT chat_id FROM {BOT_PREFIX}users"
                
                # Выполняем запрос
                rows = await conn.fetch(query)
                
                # Извлекаем chat_id из результата
                chat_ids = [row['chat_id'] for row in rows]
                logger.info(f"Получено {len(chat_ids)} chat_id пользователей из PostgreSQL")
                return chat_ids
            except Exception as e:
                logger.error(f"Ошибка при получении chat_id пользователей из PostgreSQL: {e}")
                return []
            finally:
                if conn:
                    await conn.close()
    except Exception as e:
        logger.error(f"Общая ошибка при получении chat_id пользователей: {e}")
        return []

async def send_message_to_chat(chat_id: int, message: str) -> bool:
    """
    Отправляет сообщение конкретному пользователю по chat_id.
    
    Args:
        chat_id: ID чата для отправки сообщения
        message: Текст сообщения
        
    Returns:
        bool: True, если сообщение успешно отправлено, иначе False
    """
    try:
        # Получаем экземпляр приложения
        app = get_bot_instance()
        if app is None:
            logger.error("Экземпляр бота не найден")
            return False
        
        # Отправляем сообщение с помощью bot, а не application
        await app.bot.send_message(chat_id=chat_id, text=message)
        logger.info(f"Сообщение отправлено пользователю с chat_id {chat_id}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения пользователю с chat_id {chat_id}: {e}")
        return False

async def announce(message: str, recipients: Union[List[int], str]) -> bool:
    """
    Отправляет объявление указанным получателям.
    
    Args:
        message: Текст сообщения
        recipients: Список chat_id пользователей или строка "all" для отправки всем
        
    Returns:
        bool: True, если сообщения успешно отправлены, иначе False
    """
    if not message:
        logger.error("Пустое сообщение")
        return False
    
    logger.info(f"Начинаем отправку объявления: '{message[:30]}...' получателям: {recipients}")
    
    # Определяем получателей
    chat_ids = []
    if recipients == "all":
        logger.info("Запрашиваем список всех пользователей из БД")
        # Получаем пользователей из базы данных
        chat_ids = await get_all_user_chat_ids()
        logger.info(f"Отправка объявления всем ({len(chat_ids)}) пользователям")
    elif isinstance(recipients, list):
        chat_ids = recipients
        logger.info(f"Отправка объявления {len(chat_ids)} указанным пользователям: {chat_ids}")
    elif isinstance(recipients, (int, str)) and str(recipients).isdigit():
        # Обработка одного ID пользователя
        chat_ids = [int(recipients)]
        logger.info(f"Отправка объявления одному пользователю с ID {recipients}")
    else:
        logger.error(f"Неверный формат получателей: {recipients}")
        return False
    
    if not chat_ids:
        logger.warning("Нет получателей для отправки объявления")
        
        # Если не найдено получателей в БД, используем текущего пользователя
        current_chat_id = get_chat_id_from_update(current_update)
        if current_chat_id:
            chat_ids = [current_chat_id]
            logger.info(f"Добавлен текущий пользователь (chat_id: {current_chat_id}) как получатель")
        else:
            logger.error("Не удалось получить ID чата текущего пользователя")
            return False
    
    # Убираем дубликаты
    chat_ids = list(set(chat_ids))
    logger.info(f"Итоговый список получателей: {chat_ids}")
    
    # Отправляем сообщение всем получателям
    success_count = 0
    for chat_id in chat_ids:
        logger.info(f"Отправка сообщения пользователю с chat_id {chat_id}...")
        if await send_message_to_chat(chat_id, message):
            success_count += 1
            logger.info(f"Успешно отправлено сообщение пользователю {chat_id}")
        else:
            logger.error(f"Не удалось отправить сообщение пользователю {chat_id}")
    
    logger.info(f"Объявление отправлено {success_count} из {len(chat_ids)} получателей")
    return success_count > 0 