"""
Модуль для работы с базой данных PostgreSQL.
Содержит функции для соединения, инициализации и выполнения операций с БД.
"""
import logging
import psycopg2
import pytz
from datetime import datetime
import traceback

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

# Добавим переменную для отслеживания статуса инициализации БД
_database_initialized = False

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
    """
    Инициализирует базу данных, создавая необходимые таблицы если они не существуют.
    Повторные вызовы игнорируются (инициализация происходит только один раз).
    """
    global _database_initialized
    
    # Если БД уже инициализирована, просто возвращаемся
    if _database_initialized:
        logger.info("База данных уже была инициализирована ранее")
        return True
    
    logger.info(f"Инициализация базы данных PostgreSQL (хост: {HOST}, порт: {PORT}, БД: {DATABASE})")
    
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("Не удалось подключиться к базе данных для инициализации")
            logger.error(f"Проверьте настройки подключения: HOST={HOST}, PORT={PORT}, DATABASE={DATABASE}, USER={USER}")
            return False
        
        try:
            with conn.cursor() as cursor:
                # Проверяем существуют ли таблицы
                for table_name in [USERS_TABLE, MESSAGES_TABLE, NOTIFICATIONS_TABLE]:
                    cursor.execute(f"SELECT to_regclass('public.{table_name}')")
                    exists = cursor.fetchone()[0]
                    if exists:
                        logger.info(f"Таблица {table_name} уже существует")
                    else:
                        logger.warning(f"Таблица {table_name} не существует, будет создана")
                
                # Создаем таблицу пользователей, если она не существует
                logger.info(f"Создание таблицы {USERS_TABLE} (если не существует)")
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {USERS_TABLE} (
                        user_id NUMERIC PRIMARY KEY,
                        first_name TEXT,
                        username TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                
                # Создаем таблицу сообщений
                logger.info(f"Создание таблицы {MESSAGES_TABLE} (если не существует)")
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {MESSAGES_TABLE} (
                        id SERIAL PRIMARY KEY,
                        user_id NUMERIC,
                        message_text TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                
                # Создаем таблицу уведомлений
                logger.info(f"Создание таблицы {NOTIFICATIONS_TABLE} (если не существует)")
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
                
                # Проверяем наличие столбца notification_text в таблице уведомлений
                logger.info(f"Проверка наличия столбца notification_text в таблице {NOTIFICATIONS_TABLE}")
                try:
                    cursor.execute(f"""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = '{NOTIFICATIONS_TABLE.lower()}' AND column_name = 'notification_text'
                    """)
                    has_notification_text = cursor.fetchone()
                    
                    if not has_notification_text:
                        logger.warning(f"Столбец notification_text не найден в таблице {NOTIFICATIONS_TABLE}, добавляем его")
                        cursor.execute(f"""
                            ALTER TABLE {NOTIFICATIONS_TABLE}
                            ADD COLUMN notification_text TEXT
                        """)
                        logger.info(f"Столбец notification_text успешно добавлен в таблицу {NOTIFICATIONS_TABLE}")
                except Exception as e:
                    logger.error(f"Ошибка при проверке или добавлении столбца notification_text: {e}")
                
                conn.commit()
                logger.info("Таблицы в базе данных успешно созданы/обновлены")
                
                # Проверяем структуру таблицы уведомлений
                cursor.execute(f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = '{NOTIFICATIONS_TABLE.lower()}'
                """)
                columns = cursor.fetchall()
                logger.info(f"Структура таблицы {NOTIFICATIONS_TABLE}:")
                for col_name, col_type in columns:
                    logger.info(f"  - {col_name}: {col_type}")
                    
                # Проверяем количество записей в таблице уведомлений
                cursor.execute(f"SELECT COUNT(*) FROM {NOTIFICATIONS_TABLE}")
                count = cursor.fetchone()[0]
                logger.info(f"Всего записей в таблице {NOTIFICATIONS_TABLE}: {count}")
                
                # Проверяем есть ли активные уведомления
                cursor.execute(f"SELECT COUNT(*) FROM {NOTIFICATIONS_TABLE} WHERE is_sent = FALSE")
                active_count = cursor.fetchone()[0]
                logger.info(f"Активных уведомлений в таблице {NOTIFICATIONS_TABLE}: {active_count}")
                
                # Устанавливаем флаг успешной инициализации
                _database_initialized = True
                logger.info("Установлен флаг успешной инициализации базы данных")
                
        except Exception as e:
            conn.rollback()
            logger.error(f"Ошибка при инициализации базы данных: {e}")
            logger.error(traceback.format_exc())
            return False
        finally:
            conn.close()
            
        logger.info("Инициализация базы данных завершена успешно")
        return True
        
    except Exception as e:
        logger.error(f"Критическая ошибка при инициализации базы данных: {e}")
        logger.error(traceback.format_exc())
        return False

# Функция для проверки состояния подключения к БД
def check_database_connection():
    """
    Проверяет подключение к базе данных
    """
    try:
        conn = get_db_connection()
        if conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                conn.close()
                if result and result[0] == 1:
                    logger.info("Проверка подключения к БД успешна")
                    return True
        logger.error("Проверка подключения к БД не пройдена")
        return False
    except Exception as e:
        logger.error(f"Ошибка при проверке подключения к БД: {e}")
        return False

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
    """
    Получает из базы данных все уведомления, время которых меньше или равно текущему.
    Это включает и просроченные уведомления (те, которые должны были быть отправлены ранее).
    
    Args:
        current_time (datetime): Текущее время с часовым поясом
    
    Returns:
        list: Список неотправленных уведомлений [(id, user_id, text), ...]
    """
    conn = get_db_connection()
    if not conn:
        logger.error("Не удалось подключиться к базе данных для получения уведомлений для отправки")
        return []
    
    try:
        with conn.cursor() as cursor:
            # Находим все неотправленные уведомления, время которых настало или прошло
            query = f"""
                SELECT id, user_id, notification_text 
                FROM {NOTIFICATIONS_TABLE} 
                WHERE 
                    is_sent = FALSE AND 
                    notification_time <= %s
                ORDER BY notification_time
            """
            # Логируем SQL запрос и текущее время для отладки
            logger.debug(f"SQL запрос: {query} с параметром: {current_time}")
            
            # Используем текущее время для сравнения
            cursor.execute(query, (current_time,))
            
            results = cursor.fetchall()
            if results:
                logger.debug(f"Получено {len(results)} уведомлений для отправки из БД")
                for r in results:
                    logger.debug(f"Уведомление для отправки: id={r[0]}, user_id={r[1]}, текст='{r[2]}'")
            else:
                logger.debug("Не найдено ни одного уведомления для отправки")
                
            return results
    except Exception as e:
        logger.error(f"Ошибка при получении уведомлений для отправки: {e}")
        logger.error(traceback.format_exc())
        return []
    finally:
        conn.close()

# Пометить уведомление как отправленное
def mark_notification_as_sent(notification_id):
    """
    Помечает уведомление как отправленное в базе данных
    
    Args:
        notification_id (int): ID уведомления
        
    Returns:
        bool: True если операция успешна, иначе False
    """
    # Убедимся, что notification_id имеет тип int
    notification_id = int(notification_id)
    
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