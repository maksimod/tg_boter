"""
Модуль для работы с базой данных PostgreSQL.
Содержит функции для соединения, инициализации и выполнения операций с БД.
"""
import logging
import psycopg2
import pytz
from datetime import datetime

# Импортируем конфигурации
from credentials.postgres.config import HOST, PORT, DATABASE, USER, PASSWORD, BOT_PREFIX

# Получаем логгер
logger = logging.getLogger(__name__)

# Таблицы в базе данных
USERS_TABLE = f"{BOT_PREFIX}users"
MESSAGES_TABLE = f"{BOT_PREFIX}messages"
NOTIFICATIONS_TABLE = f"{BOT_PREFIX}notifications"

# Московское время (UTC+3)
MOSCOW_TZ = pytz.timezone('Europe/Moscow')

# Функция для создания соединения с БД
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=HOST,
            port=PORT,
            database=DATABASE,
            user=USER,
            password=PASSWORD
        )
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        return None

# Функция для инициализации базы данных
def init_database():
    conn = get_db_connection()
    if not conn:
        logger.error("Не удалось подключиться к базе данных для инициализации")
        return
    
    try:
        with conn.cursor() as cursor:
            # Создаем таблицу пользователей, если она не существует
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {USERS_TABLE} (
                    user_id NUMERIC PRIMARY KEY,
                    first_name TEXT,
                    username TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Создаем таблицу сообщений
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {MESSAGES_TABLE} (
                    id SERIAL PRIMARY KEY,
                    user_id NUMERIC,
                    message_text TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Создаем таблицу уведомлений
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {NOTIFICATIONS_TABLE} (
                    id SERIAL PRIMARY KEY,
                    user_id NUMERIC,
                    notification_text TEXT,
                    notification_time TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    is_sent BOOLEAN DEFAULT FALSE
                )
            """)
            
            conn.commit()
            logger.info("Таблицы в базе данных успешно созданы")
    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка при инициализации базы данных: {e}")
    finally:
        conn.close()

# Функция для сохранения пользователя в БД
def save_user(user_id, first_name, username):
    conn = get_db_connection()
    if not conn:
        logger.error("Не удалось подключиться к базе данных для сохранения пользователя")
        return
    
    try:
        with conn.cursor() as cursor:
            # Проверяем, существует ли пользователь
            cursor.execute(
                f"SELECT user_id FROM {USERS_TABLE} WHERE user_id = %s",
                (user_id,)
            )
            if cursor.fetchone() is None:
                # Если пользователя нет, то добавляем его
                cursor.execute(
                    f"INSERT INTO {USERS_TABLE} (user_id, first_name, username) VALUES (%s, %s, %s)",
                    (user_id, first_name, username)
                )
                conn.commit()
                logger.info(f"Новый пользователь добавлен: {user_id}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка при сохранении пользователя: {e}")
    finally:
        conn.close()

# Функция для сохранения сообщения в БД
def save_message(user_id, message_text):
    conn = get_db_connection()
    if not conn:
        logger.error("Не удалось подключиться к базе данных для сохранения сообщения")
        return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO {MESSAGES_TABLE} (user_id, message_text) VALUES (%s, %s)",
                (user_id, message_text)
            )
            conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка при сохранении сообщения: {e}")
    finally:
        conn.close()

# Функция для создания уведомления в БД
def create_notification(user_id, message, notification_time):
    conn = get_db_connection()
    if not conn:
        logger.error("Не удалось подключиться к базе данных для создания уведомления")
        return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO {NOTIFICATIONS_TABLE} (user_id, notification_text, notification_time) VALUES (%s, %s, %s) RETURNING id",
                (user_id, message, notification_time)
            )
            notification_id = cursor.fetchone()[0]
            conn.commit()
            logger.info(f"Создано новое уведомление #{notification_id} для пользователя {user_id} на {notification_time.strftime('%d.%m.%Y %H:%M:%S %z')}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка при создании уведомления: {e}")
    finally:
        conn.close()

# Функция для получения активных уведомлений пользователя
def get_user_notifications(user_id):
    conn = get_db_connection()
    if not conn:
        logger.error("Не удалось подключиться к базе данных для получения уведомлений")
        return []
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"SELECT id, notification_text, notification_time FROM {NOTIFICATIONS_TABLE} WHERE user_id = %s AND is_sent = FALSE ORDER BY notification_time",
                (user_id,)
            )
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Ошибка при получении уведомлений пользователя: {e}")
        return []
    finally:
        conn.close()

# Получить все уведомления, которые нужно отправить
def get_notifications_to_send(current_time):
    conn = get_db_connection()
    if not conn:
        logger.error("Не удалось подключиться к базе данных для получения уведомлений для отправки")
        return []
    
    try:
        with conn.cursor() as cursor:
            # Находим все неотправленные уведомления, время которых настало
            query = f"""
                SELECT id, user_id, notification_text 
                FROM {NOTIFICATIONS_TABLE} 
                WHERE 
                    is_sent = FALSE AND 
                    notification_time <= %s
            """
            # Используем текущее время для сравнения
            params = (current_time,)
            
            cursor.execute(query, params)
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Ошибка при получении уведомлений для отправки: {e}")
        return []
    finally:
        conn.close()

# Пометить уведомление как отправленное
def mark_notification_as_sent(notification_id):
    conn = get_db_connection()
    if not conn:
        logger.error("Не удалось подключиться к базе данных для обновления статуса уведомления")
        return False
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"UPDATE {NOTIFICATIONS_TABLE} SET is_sent = TRUE WHERE id = %s",
                (notification_id,)
            )
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка при обновлении статуса уведомления: {e}")
        return False
    finally:
        conn.close()

# Получить все активные уведомления
def get_all_active_notifications():
    conn = get_db_connection()
    if not conn:
        logger.error("Не удалось подключиться к базе данных для получения всех активных уведомлений")
        return []
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"SELECT id, user_id, notification_text, notification_time, is_sent FROM {NOTIFICATIONS_TABLE} WHERE is_sent = FALSE"
            )
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Ошибка при получении всех активных уведомлений: {e}")
        return []
    finally:
        conn.close()

# Исправить часовые пояса уведомлений
def fix_notification_timezone(notification_id, notification_time):
    conn = get_db_connection()
    if not conn:
        logger.error("Не удалось подключиться к базе данных для исправления часового пояса уведомления")
        return False
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"UPDATE {NOTIFICATIONS_TABLE} SET notification_time = %s WHERE id = %s",
                (notification_time, notification_id)
            )
            conn.commit()
            return True
    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка при исправлении часового пояса уведомления: {e}")
        return False
    finally:
        conn.close()

# Получить текущее время сервера БД
def get_db_time():
    conn = get_db_connection()
    if not conn:
        logger.error("Не удалось подключиться к базе данных для получения времени сервера")
        return None
    
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT NOW()")
            return cursor.fetchone()[0]
    except Exception as e:
        logger.error(f"Ошибка при получении времени сервера БД: {e}")
        return None
    finally:
        conn.close()

# Получить все уведомления пользователя (включая отправленные)
def get_all_user_notifications(user_id):
    conn = get_db_connection()
    if not conn:
        logger.error("Не удалось подключиться к базе данных для получения всех уведомлений пользователя")
        return []
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"SELECT id, notification_text, notification_time, is_sent FROM {NOTIFICATIONS_TABLE} WHERE user_id = %s ORDER BY notification_time",
                (user_id,)
            )
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Ошибка при получении всех уведомлений пользователя: {e}")
        return []
    finally:
        conn.close() 