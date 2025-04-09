import asyncio
import logging
import asyncpg
import sys

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('postgres_test')

async def test_postgres_connection():
    """
    Тестирует соединение с PostgreSQL и получает список пользователей.
    """
    conn = None
    try:
        # Загружаем настройки PostgreSQL
        from credentials.postgres.config import HOST, PORT, DATABASE, USER, PASSWORD, BOT_PREFIX
        
        logger.info("Загружены настройки PostgreSQL:")
        logger.info(f"Хост: {HOST}")
        logger.info(f"Порт: {PORT}")
        logger.info(f"База данных: {DATABASE}")
        logger.info(f"Пользователь: {USER}")
        logger.info(f"Префикс: {BOT_PREFIX}")
        
        # Устанавливаем соединение
        logger.info(f"Подключение к PostgreSQL: {HOST}:{PORT}, БД: {DATABASE}, пользователь: {USER}")
        
        conn = await asyncpg.connect(
            host=HOST,
            port=PORT,
            user=USER,
            password=PASSWORD,
            database=DATABASE,
            timeout=10.0
        )
        
        # Проверяем соединение
        result = await conn.fetchval("SELECT 1")
        logger.info(f"Проверка соединения: {result}")
        
        # Проверяем существующие таблицы
        tables = await conn.fetch(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
        )
        logger.info(f"Доступные таблицы в базе данных: {[table['table_name'] for table in tables]}")
        
        # Проверяем таблицу пользователей
        users_table = f"{BOT_PREFIX}users"
        table_exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name=$1)",
            users_table
        )
        
        if not table_exists:
            logger.error(f"Таблица {users_table} не существует!")
            return
            
        logger.info(f"Таблица {users_table} существует")
        
        # Получаем структуру таблицы
        columns = await conn.fetch(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name=$1",
            users_table
        )
        logger.info(f"Структура таблицы {users_table}: {[(col['column_name'], col['data_type']) for col in columns]}")
        
        # Получаем количество пользователей
        user_count = await conn.fetchval(f"SELECT COUNT(*) FROM {users_table}")
        logger.info(f"Количество пользователей в таблице {users_table}: {user_count}")
        
        # Получаем chat_id пользователей
        if user_count > 0:
            chat_ids = await conn.fetch(f"SELECT DISTINCT chat_id FROM {users_table}")
            logger.info(f"Chat IDs пользователей: {[row['chat_id'] for row in chat_ids]}")
        
        logger.info("Тест соединения с PostgreSQL успешно завершен")
        
    except Exception as e:
        logger.error(f"Ошибка при тестировании PostgreSQL: {e}")
        
    finally:
        if conn:
            await conn.close()
            logger.info("Соединение с PostgreSQL закрыто")

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(test_postgres_connection())
    except KeyboardInterrupt:
        logger.info("Тест прерван пользователем")
    except Exception as e:
        logger.error(f"Необработанная ошибка: {e}")
        sys.exit(1)
    finally:
        logger.info("Тест завершен") 