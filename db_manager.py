import asyncio
import logging
import os
from asyncio import Lock
from typing import Optional, List, Dict, Any, Tuple

# Настраиваем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

try:
    import asyncpg
    logger.info("PostgreSQL модуль импортирован успешно")
except ImportError as e:
    logger.error(f"Ошибка импорта PostgreSQL модуля: {e}")
    logger.info("Устанавливаем asyncpg...")
    os.system("pip install asyncpg")
    try:
        import asyncpg
        logger.info("PostgreSQL модуль установлен успешно")
    except ImportError:
        logger.error("Не удалось установить asyncpg. Пожалуйста, установите вручную: pip install asyncpg")
        asyncpg = None

class DatabaseManager:
    """Класс для управления подключением к базе данных и выполнения запросов"""
    
    def __init__(self):
        self.db_host = None
        self.db_port = None
        self.db_name = None
        self.db_user = None
        self.db_password = None
        self.bot_prefix = "tgbot_"  # Префикс по умолчанию
        self.db_lock = Lock()  # Блокировка для операций с БД
        self.initialized = False
    
    async def initialize(self) -> bool:
        """Инициализирует соединение с PostgreSQL и создает таблицы"""
        if asyncpg is None:
            logger.error("PostgreSQL не доступен - модуль asyncpg не установлен")
            return False
        
        # Загружаем конфигурацию
        if not self._load_config():
            logger.error("Не удалось загрузить настройки PostgreSQL")
            return False
        
        try:
            logger.info(f"Подключение к PostgreSQL: {self.db_host}:{self.db_port}, DB: {self.db_name}, User: {self.db_user}")
            
            # Проверяем соединение
            connection = await self._get_connection()
            if connection is None:
                logger.error("Не удалось создать соединение с PostgreSQL")
                return False
                
            try:
                # Проверяем соединение
                await connection.execute("SELECT 1")
                logger.info("Соединение с PostgreSQL успешно установлено")
                
                # Создаем таблицы
                self.initialized = await self._create_tables(connection)
                
                return self.initialized
            finally:
                # Закрываем соединение в любом случае
                await connection.close()
                
        except Exception as e:
            logger.error(f"Ошибка при инициализации PostgreSQL: {e}")
            return False
    
    def _load_config(self) -> bool:
        """Загружает настройки подключения к PostgreSQL"""
        try:
            # Проверяем наличие папки credentials/postgres
            if os.path.exists("credentials/postgres"):
                try:
                    from credentials.postgres.config import (
                        HOST, DATABASE, USER, PASSWORD, PORT, BOT_PREFIX
                    )
                    self.db_host = HOST
                    self.db_port = PORT
                    self.db_name = DATABASE
                    self.db_user = USER
                    self.db_password = PASSWORD
                    self.bot_prefix = BOT_PREFIX if BOT_PREFIX else self.bot_prefix
                    logger.info(f"Настройки PostgreSQL загружены из config.py. BOT_PREFIX: {self.bot_prefix}")
                    return True
                except ImportError:
                    logger.error("Не удалось загрузить настройки PostgreSQL из модуля")
                except Exception as e:
                    logger.error(f"Ошибка при загрузке настроек PostgreSQL: {e}")
                    
        except Exception as e:
            logger.error(f"Ошибка при загрузке настроек PostgreSQL: {e}")
        
        logger.error("Не удалось загрузить настройки PostgreSQL")
        return False
    
    async def _get_connection(self):
        """Создает новое соединение с базой данных"""
        if asyncpg is None:
            logger.error("PostgreSQL не доступен - модуль asyncpg не установлен")
            return None
        
        if None in (self.db_host, self.db_port, self.db_name, self.db_user, self.db_password):
            logger.error("Настройки PostgreSQL не загружены")
            return None
            
        try:
            # Создаем новое соединение для каждой операции
            connection = await asyncpg.connect(
                host=self.db_host,
                port=self.db_port,
                user=self.db_user,
                password=self.db_password,
                database=self.db_name,
                timeout=10.0,
                command_timeout=10.0,
                ssl=False
            )
            return connection
        except Exception as e:
            logger.error(f"Ошибка при создании соединения с БД: {e}")
            return None
    
    async def _create_tables(self, connection=None) -> bool:
        """Создает необходимые таблицы в базе данных"""
        if asyncpg is None:
            logger.error("PostgreSQL не доступен - модуль asyncpg не установлен")
            return False
        
        # Если соединение не передано, создаем новое
        close_conn = False
        if connection is None:
            connection = await self._get_connection()
            close_conn = True
            
        if connection is None:
            logger.error("Не удалось создать соединение с PostgreSQL")
            return False
        
        try:
            # Таблица пользователей
            await connection.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.bot_prefix}users (
                    id SERIAL PRIMARY KEY,
                    chat_id BIGINT NOT NULL,
                    user_id BIGINT NOT NULL,
                    username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id)
                )
            ''')
            
            # Таблица сообщений
            await connection.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.bot_prefix}messages (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES {self.bot_prefix}users(id),
                    message_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица переводов
            await connection.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.bot_prefix}translations (
                    id SERIAL PRIMARY KEY,
                    source_text TEXT NOT NULL,
                    translated_text TEXT NOT NULL,
                    source_language VARCHAR(50) NOT NULL,
                    target_language VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(source_text, target_language)
                )
            ''')
            
            # Таблица напоминаний
            await connection.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.bot_prefix}notifications (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES {self.bot_prefix}users(id),
                    text TEXT NOT NULL,
                    notification_time TIME NOT NULL,
                    notification_date DATE NOT NULL,
                    is_sent BOOLEAN DEFAULT FALSE,
                    is_deleted BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            logger.info(f"Таблицы с префиксом '{self.bot_prefix}' созданы")
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при создании таблиц: {e}")
            return False
        finally:
            # Если мы создали соединение внутри этой функции, закрываем его
            if close_conn and connection is not None:
                await connection.close()
    
    async def add_user(self, user_id: int, chat_id: int, username: str) -> Optional[int]:
        """Добавляет пользователя в базу данных"""
        if not self.initialized:
            logger.error("PostgreSQL не инициализирован")
            return None
        
        max_retries = 3
        for attempt in range(max_retries):
            connection = None
            try:
                async with self.db_lock:
                    # Создаем новое соединение
                    connection = await self._get_connection()
                    if connection is None:
                        if attempt < max_retries - 1:
                            logger.warning("Не удалось создать соединение, пробуем снова...")
                            await asyncio.sleep(1)
                            continue
                        else:
                            logger.error("Не удалось создать соединение после всех попыток")
                            return None
                    
                    # Проверяем, существует ли пользователь
                    user = await connection.fetchrow(
                        f"SELECT id FROM {self.bot_prefix}users WHERE user_id = $1",
                        user_id
                    )
                    
                    if user:
                        logger.info(f"Пользователь {user_id} уже существует в БД")
                        return user['id']
                    
                    # Добавляем нового пользователя
                    user_id_in_db = await connection.fetchval(
                        f'''
                        INSERT INTO {self.bot_prefix}users (user_id, chat_id, username)
                        VALUES ($1, $2, $3)
                        RETURNING id
                        ''',
                        user_id, chat_id, username
                    )
                    
                    logger.info(f"Добавлен новый пользователь: {username} (ID: {user_id})")
                    return user_id_in_db
                    
            except Exception as e:
                logger.error(f"Ошибка при добавлении пользователя (попытка {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info("Повторная попытка через 1 секунду...")
                    await asyncio.sleep(1)
                else:
                    return None
            finally:
                # Закрываем соединение в любом случае
                if connection:
                    await connection.close()
        
        return None
    
    async def add_message(self, user_db_id: int, message_text: str) -> bool:
        """Добавляет сообщение в базу данных"""
        if not self.initialized:
            logger.error("PostgreSQL не инициализирован")
            return False
        
        max_retries = 3
        for attempt in range(max_retries):
            connection = None
            try:
                async with self.db_lock:
                    # Создаем новое соединение
                    connection = await self._get_connection()
                    if connection is None:
                        if attempt < max_retries - 1:
                            logger.warning("Не удалось создать соединение, пробуем снова...")
                            await asyncio.sleep(1)
                            continue
                        else:
                            logger.error("Не удалось создать соединение после всех попыток")
                            return False
                    
                    await connection.execute(
                        f'''
                        INSERT INTO {self.bot_prefix}messages (user_id, message_text)
                        VALUES ($1, $2)
                        ''',
                        user_db_id, message_text
                    )
                    
                    return True
                    
            except Exception as e:
                logger.error(f"Ошибка при добавлении сообщения (попытка {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info("Повторная попытка через 1 секунду...")
                    await asyncio.sleep(1)
                else:
                    return False
            finally:
                # Закрываем соединение в любом случае
                if connection:
                    await connection.close()
        
        return False
    
    async def delete_user_data(self, user_id: int) -> bool:
        """Удаляет пользователя и все его сообщения из базы данных"""
        if not self.initialized:
            logger.error("PostgreSQL не инициализирован")
            return False
        
        max_retries = 3
        for attempt in range(max_retries):
            connection = None
            try:
                async with self.db_lock:
                    # Создаем новое соединение
                    connection = await self._get_connection()
                    if connection is None:
                        if attempt < max_retries - 1:
                            logger.warning("Не удалось создать соединение, пробуем снова...")
                            await asyncio.sleep(1)
                            continue
                        else:
                            logger.error("Не удалось создать соединение после всех попыток")
                            return False
                    
                    # Находим ID пользователя в БД
                    db_user_id = await connection.fetchval(
                        f"SELECT id FROM {self.bot_prefix}users WHERE user_id = $1",
                        user_id
                    )
                    
                    if not db_user_id:
                        logger.warning(f"Пользователь {user_id} не найден в БД")
                        return False
                    
                    # Начинаем транзакцию для последовательного удаления
                    async with connection.transaction():
                        # Удаляем все напоминания пользователя
                        await connection.execute(
                            f"DELETE FROM {self.bot_prefix}notifications WHERE user_id = $1",
                            db_user_id
                        )
                        
                        # Удаляем все сообщения пользователя
                        await connection.execute(
                            f"DELETE FROM {self.bot_prefix}messages WHERE user_id = $1",
                            db_user_id
                        )
                        
                        logger.info(f"Удалены все сообщения и напоминания пользователя {user_id}")
                        
                        # Удаляем самого пользователя
                        await connection.execute(
                            f"DELETE FROM {self.bot_prefix}users WHERE id = $1",
                            db_user_id
                        )
                        
                        logger.info(f"Пользователь {user_id} удален из БД")
                    
                    return True
                    
            except Exception as e:
                logger.error(f"Ошибка при удалении пользователя (попытка {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info("Повторная попытка через 1 секунду...")
                    await asyncio.sleep(1)
                else:
                    return False
            finally:
                # Закрываем соединение в любом случае
                if connection:
                    await connection.close()
        
        return False
    
    async def add_notification(self, user_db_id: int, text: str, notification_time: str, notification_date: str) -> Optional[int]:
        """Добавляет напоминание в базу данных"""
        if not self.initialized:
            logger.error("PostgreSQL не инициализирован")
            return None
        
        max_retries = 3
        for attempt in range(max_retries):
            connection = None
            try:
                async with self.db_lock:
                    # Создаем новое соединение
                    connection = await self._get_connection()
                    if connection is None:
                        if attempt < max_retries - 1:
                            logger.warning("Не удалось создать соединение, пробуем снова...")
                            await asyncio.sleep(1)
                            continue
                        else:
                            logger.error("Не удалось создать соединение после всех попыток")
                            return None
                    
                    # Добавляем новое напоминание
                    notification_id = await connection.fetchval(
                        f'''
                        INSERT INTO {self.bot_prefix}notifications 
                        (user_id, text, notification_time, notification_date)
                        VALUES ($1, $2, $3, $4)
                        RETURNING id
                        ''',
                        user_db_id, text, notification_time, notification_date
                    )
                    
                    logger.info(f"Добавлено новое напоминание (ID: {notification_id}) для пользователя DB ID: {user_db_id}")
                    return notification_id
                    
            except Exception as e:
                logger.error(f"Ошибка при добавлении напоминания (попытка {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info("Повторная попытка через 1 секунду...")
                    await asyncio.sleep(1)
                else:
                    return None
            finally:
                # Закрываем соединение в любом случае
                if connection:
                    await connection.close()
        
        return None
    
    async def get_user_notifications(self, user_db_id: int, show_sent: bool = False, show_deleted: bool = False) -> List[Dict[str, Any]]:
        """Получает список напоминаний пользователя"""
        if not self.initialized:
            logger.error("PostgreSQL не инициализирован")
            return []
        
        max_retries = 3
        for attempt in range(max_retries):
            connection = None
            try:
                async with self.db_lock:
                    # Создаем новое соединение
                    connection = await self._get_connection()
                    if connection is None:
                        if attempt < max_retries - 1:
                            logger.warning("Не удалось создать соединение, пробуем снова...")
                            await asyncio.sleep(1)
                            continue
                        else:
                            logger.error("Не удалось создать соединение после всех попыток")
                            return []
                    
                    # Формируем условия для выборки
                    conditions = ["user_id = $1"]
                    
                    if not show_sent:
                        conditions.append("is_sent = FALSE")
                    
                    if not show_deleted:
                        conditions.append("is_deleted = FALSE")
                    
                    where_clause = " AND ".join(conditions)
                    
                    # Получаем напоминания
                    rows = await connection.fetch(
                        f'''
                        SELECT id, text, notification_time, notification_date, is_sent, is_deleted
                        FROM {self.bot_prefix}notifications
                        WHERE {where_clause}
                        ORDER BY notification_date ASC, notification_time ASC
                        ''',
                        user_db_id
                    )
                    
                    # Преобразуем результаты в список словарей
                    notifications = []
                    for row in rows:
                        notifications.append({
                            'id': row['id'],
                            'text': row['text'],
                            'time': row['notification_time'].strftime('%H:%M'),
                            'date': row['notification_date'].strftime('%d.%m.%Y'),
                            'is_sent': row['is_sent'],
                            'is_deleted': row['is_deleted']
                        })
                    
                    return notifications
                    
            except Exception as e:
                logger.error(f"Ошибка при получении напоминаний (попытка {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info("Повторная попытка через 1 секунду...")
                    await asyncio.sleep(1)
                else:
                    return []
            finally:
                # Закрываем соединение в любом случае
                if connection:
                    await connection.close()
        
        return []
    
    async def delete_notification(self, notification_id: int) -> bool:
        """Помечает напоминание как удаленное"""
        if not self.initialized:
            logger.error("PostgreSQL не инициализирован")
            return False
        
        max_retries = 3
        for attempt in range(max_retries):
            connection = None
            try:
                async with self.db_lock:
                    # Создаем новое соединение
                    connection = await self._get_connection()
                    if connection is None:
                        if attempt < max_retries - 1:
                            logger.warning("Не удалось создать соединение, пробуем снова...")
                            await asyncio.sleep(1)
                            continue
                        else:
                            logger.error("Не удалось создать соединение после всех попыток")
                            return False
                    
                    # Помечаем напоминание как удаленное
                    result = await connection.execute(
                        f'''
                        UPDATE {self.bot_prefix}notifications
                        SET is_deleted = TRUE
                        WHERE id = $1
                        ''',
                        notification_id
                    )
                    
                    # Проверяем результат (должно быть UPDATE 1)
                    affected = result.split()[1]
                    success = affected == '1'
                    
                    if success:
                        logger.info(f"Напоминание {notification_id} помечено как удаленное")
                    else:
                        logger.warning(f"Напоминание {notification_id} не найдено")
                    
                    return success
                    
            except Exception as e:
                logger.error(f"Ошибка при удалении напоминания (попытка {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info("Повторная попытка через 1 секунду...")
                    await asyncio.sleep(1)
                else:
                    return False
            finally:
                # Закрываем соединение в любом случае
                if connection:
                    await connection.close()
        
        return False
    
    async def get_active_notifications(self, current_date: str, current_time: str) -> List[Dict[str, Any]]:
        """Получает список активных напоминаний на текущее время"""
        if not self.initialized:
            logger.error("PostgreSQL не инициализирован")
            return []
        
        max_retries = 3
        for attempt in range(max_retries):
            connection = None
            try:
                async with self.db_lock:
                    # Создаем новое соединение
                    connection = await self._get_connection()
                    if connection is None:
                        if attempt < max_retries - 1:
                            logger.warning("Не удалось создать соединение, пробуем снова...")
                            await asyncio.sleep(1)
                            continue
                        else:
                            logger.error("Не удалось создать соединение после всех попыток")
                            return []
                    
                    # Получаем активные напоминания
                    rows = await connection.fetch(
                        f'''
                        SELECT n.id, n.text, n.notification_time, n.notification_date,
                               u.user_id, u.chat_id
                        FROM {self.bot_prefix}notifications n
                        JOIN {self.bot_prefix}users u ON n.user_id = u.id
                        WHERE n.notification_date = $1
                          AND n.notification_time <= $2
                          AND n.is_sent = FALSE
                          AND n.is_deleted = FALSE
                        ''',
                        current_date, current_time
                    )
                    
                    # Преобразуем результаты в список словарей
                    notifications = []
                    for row in rows:
                        notifications.append({
                            'id': row['id'],
                            'text': row['text'],
                            'time': row['notification_time'].strftime('%H:%M'),
                            'date': row['notification_date'].strftime('%d.%m.%Y'),
                            'user_id': row['user_id'],
                            'chat_id': row['chat_id']
                        })
                    
                    return notifications
                    
            except Exception as e:
                logger.error(f"Ошибка при получении активных напоминаний (попытка {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info("Повторная попытка через 1 секунду...")
                    await asyncio.sleep(1)
                else:
                    return []
            finally:
                # Закрываем соединение в любом случае
                if connection:
                    await connection.close()
        
        return []
    
    async def mark_notification_as_sent(self, notification_id: int) -> bool:
        """Помечает напоминание как отправленное"""
        if not self.initialized:
            logger.error("PostgreSQL не инициализирован")
            return False
        
        max_retries = 3
        for attempt in range(max_retries):
            connection = None
            try:
                async with self.db_lock:
                    # Создаем новое соединение
                    connection = await self._get_connection()
                    if connection is None:
                        if attempt < max_retries - 1:
                            logger.warning("Не удалось создать соединение, пробуем снова...")
                            await asyncio.sleep(1)
                            continue
                        else:
                            logger.error("Не удалось создать соединение после всех попыток")
                            return False
                    
                    # Помечаем напоминание как отправленное
                    result = await connection.execute(
                        f'''
                        UPDATE {self.bot_prefix}notifications
                        SET is_sent = TRUE
                        WHERE id = $1
                        ''',
                        notification_id
                    )
                    
                    # Проверяем результат (должно быть UPDATE 1)
                    affected = result.split()[1]
                    success = affected == '1'
                    
                    if success:
                        logger.info(f"Напоминание {notification_id} помечено как отправленное")
                    else:
                        logger.warning(f"Напоминание {notification_id} не найдено")
                    
                    return success
                    
            except Exception as e:
                logger.error(f"Ошибка при отметке напоминания (попытка {attempt+1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info("Повторная попытка через 1 секунду...")
                    await asyncio.sleep(1)
                else:
                    return False
            finally:
                # Закрываем соединение в любом случае
                if connection:
                    await connection.close()
        
        return False 