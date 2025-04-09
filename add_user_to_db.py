import asyncio
import asyncpg
import logging
import sys
import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('user_adder')

async def init_postgres():
    """
    Инициализирует подключение к PostgreSQL и создает необходимые таблицы
    """
    conn = None
    try:
        # Загружаем настройки PostgreSQL
        from credentials.postgres.config import HOST, PORT, DATABASE, USER, PASSWORD, BOT_PREFIX
        
        logger.info(f"Инициализация PostgreSQL: {HOST}:{PORT}, БД: {DATABASE}, пользователь: {USER}")
        
        # Устанавливаем соединение
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
        
        # Создаем необходимые таблицы
        users_table = f"{BOT_PREFIX}users"
        notifications_table = f"{BOT_PREFIX}notifications"
        
        # Создаем таблицу пользователей
        await conn.execute(f'''
            CREATE TABLE IF NOT EXISTS {users_table} (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id)
            )
        ''')
        
        # Создаем таблицу уведомлений с правильной структурой
        await conn.execute(f'''
            CREATE TABLE IF NOT EXISTS {notifications_table} (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                notification_text TEXT,
                notification_time TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                is_sent BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Проверяем структуру таблицы уведомлений и добавляем отсутствующие столбцы
        await check_notifications_table_structure(conn, notifications_table)
        
        logger.info(f"Таблицы {users_table} и {notifications_table} успешно созданы/проверены")
        return True
    except Exception as e:
        logger.error(f"Ошибка при инициализации PostgreSQL: {e}")
        return False
    finally:
        if conn:
            await conn.close()
            logger.info("Соединение с PostgreSQL закрыто")

async def check_notifications_table_structure(conn, notifications_table):
    """
    Проверяет и исправляет структуру таблицы уведомлений
    """
    try:
        # Проверяем наличие столбца notification_text
        has_column = await conn.fetchval(f'''
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = $1
                AND column_name = 'notification_text'
            )
        ''', notifications_table.lower())
        
        if not has_column:
            logger.warning(f"Столбец notification_text отсутствует в таблице {notifications_table}, добавляем его")
            await conn.execute(f'''
                ALTER TABLE {notifications_table}
                ADD COLUMN notification_text TEXT
            ''')
            logger.info(f"Столбец notification_text успешно добавлен в таблицу {notifications_table}")
        else:
            logger.info(f"Столбец notification_text присутствует в таблице {notifications_table}")
            
    except Exception as e:
        logger.error(f"Ошибка при проверке/исправлении структуры таблицы уведомлений: {e}")

async def add_user_to_db(user_id: int, chat_id: int, username: str = "test_user"):
    """
    Добавляет пользователя в базу данных PostgreSQL
    """
    conn = None
    try:
        # Загружаем настройки PostgreSQL
        from credentials.postgres.config import HOST, PORT, DATABASE, USER, PASSWORD, BOT_PREFIX
        
        logger.info(f"Подключение к PostgreSQL: {HOST}:{PORT}, БД: {DATABASE}, пользователь: {USER}")
        
        # Устанавливаем соединение
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
        
        # Проверяем существование таблицы пользователей
        users_table = f"{BOT_PREFIX}users"
        table_exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name=$1)",
            users_table
        )
        
        if not table_exists:
            logger.error(f"Таблица {users_table} не существует! Создаем...")
            # Создаем таблицу пользователей, если она не существует
            await conn.execute(f'''
                CREATE TABLE {users_table} (
                    id SERIAL PRIMARY KEY,
                    chat_id BIGINT NOT NULL,
                    user_id BIGINT NOT NULL,
                    username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id)
                )
            ''')
            logger.info(f"Таблица {users_table} успешно создана")
        
        # Проверяем, существует ли пользователь с таким user_id
        existing_user = await conn.fetchval(
            f"SELECT id FROM {users_table} WHERE user_id = $1",
            user_id
        )
        
        if existing_user:
            # Обновляем данные пользователя
            await conn.execute(
                f"UPDATE {users_table} SET chat_id = $1, username = $2 WHERE user_id = $3",
                chat_id, username, user_id
            )
            logger.info(f"Пользователь {user_id} обновлен в базе данных")
        else:
            # Добавляем нового пользователя
            await conn.execute(
                f"INSERT INTO {users_table} (chat_id, user_id, username) VALUES ($1, $2, $3)",
                chat_id, user_id, username
            )
            logger.info(f"Пользователь {user_id} добавлен в базу данных")
        
        # Проверяем, что пользователь действительно добавлен
        check_user = await conn.fetchval(
            f"SELECT id FROM {users_table} WHERE user_id = $1",
            user_id
        )
        
        if check_user:
            logger.info(f"Проверка пройдена: пользователь {user_id} существует в базе данных")
            return True
        else:
            logger.error(f"Проверка не пройдена: пользователь {user_id} отсутствует в базе данных!")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя в базу данных: {e}")
        return False
    finally:
        if conn:
            await conn.close()
            logger.info("Соединение с PostgreSQL закрыто")

async def get_all_users():
    """
    Получает список всех пользователей из базы данных PostgreSQL
    
    Returns:
        list: Список пользователей в формате [{user_id, chat_id, username}]
    """
    conn = None
    try:
        # Загружаем настройки PostgreSQL
        from credentials.postgres.config import HOST, PORT, DATABASE, USER, PASSWORD, BOT_PREFIX
        
        logger.info(f"Подключение к PostgreSQL: {HOST}:{PORT}, БД: {DATABASE}, пользователь: {USER}")
        
        # Устанавливаем соединение
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
        users_table = f"{BOT_PREFIX}users"
        users = await conn.fetch(f"SELECT user_id, chat_id, username FROM {users_table}")
        
        logger.info(f"Получено {len(users)} пользователей из базы данных")
        return users
            
    except Exception as e:
        logger.error(f"Ошибка при получении списка пользователей из базы данных: {e}")
        return []
    finally:
        if conn:
            await conn.close()
            logger.info("Соединение с PostgreSQL закрыто")

async def test_send_announcement():
    """
    Тестирует отправку объявления
    """
    try:
        from announcement import announce
        from easy_bot import get_bot_instance
        
        # Проверяем, что бот доступен
        bot_app = get_bot_instance()
        if bot_app is None:
            logger.error("Бот не инициализирован! Запустите бота перед отправкой тестового объявления")
            print("\n❌ Бот не запущен. Запустите бота в отдельном терминале, затем повторите попытку.")
            return False
        
        # Получаем ID текущего пользователя из аргументов командной строки или используем пользователя из БД
        chat_id = None
        if len(sys.argv) > 2:
            chat_id = int(sys.argv[2])
            logger.info(f"Используем chat_id из аргументов командной строки: {chat_id}")
        else:
            # Проверяем наличие пользователей в базе
            from credentials.postgres.config import HOST, PORT, DATABASE, USER, PASSWORD, BOT_PREFIX
            conn = await asyncpg.connect(
                host=HOST, port=PORT, user=USER, password=PASSWORD, database=DATABASE
            )
            users = await conn.fetch(f"SELECT chat_id FROM {BOT_PREFIX}users LIMIT 1")
            await conn.close()
            
            if not users:
                logger.error("В базе данных нет пользователей! Используйте команду:")
                logger.error("python add_user_to_db.py add YOUR_CHAT_ID YOUR_USER_ID")
                print("\n❌ В базе данных нет пользователей. Сначала добавьте пользователя командой:")
                print("  python add_user_to_db.py add CHAT_ID USER_ID [USERNAME]")
                return False
                
            chat_id = users[0]['chat_id']
            logger.info(f"Используем chat_id из базы данных: {chat_id}")
        
        logger.info(f"Отправка тестового объявления пользователю с chat_id {chat_id}")
        
        # Отправляем тестовое объявление
        test_message = "Это тестовое объявление для проверки работы функции объявлений"
        success = await announce(test_message, [chat_id])
        
        if success:
            logger.info(f"Тестовое объявление успешно отправлено пользователю {chat_id}")
            return True
        else:
            logger.error(f"Не удалось отправить тестовое объявление пользователю {chat_id}")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при тестировании отправки объявления: {e}")
        import traceback
        traceback.print_exc()
        return False

async def add_test_notification():
    """
    Добавляет тестовое уведомление в базу данных
    """
    conn = None
    try:
        # Загружаем настройки PostgreSQL
        from credentials.postgres.config import HOST, PORT, DATABASE, USER, PASSWORD, BOT_PREFIX
        
        logger.info(f"Подключение к PostgreSQL для добавления тестового уведомления")
        
        # Устанавливаем соединение
        conn = await asyncpg.connect(
            host=HOST,
            port=PORT,
            user=USER,
            password=PASSWORD,
            database=DATABASE,
            timeout=10.0
        )
        
        # Получаем пользователя для тестового уведомления
        users = await conn.fetch(f"SELECT user_id FROM {BOT_PREFIX}users LIMIT 1")
        
        if not users:
            logger.error("Не найдено пользователей для создания тестового уведомления")
            print("\n❌ Не найдено пользователей. Сначала добавьте пользователя командой:")
            print("  python add_user_to_db.py add CHAT_ID USER_ID [USERNAME]")
            return False
        
        user_id = users[0]['user_id']
        
        # Создаем уведомление через 1 минуту от текущего времени
        notification_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=1)
        notification_text = "Это тестовое уведомление, созданное скриптом add_user_to_db.py"
        
        # Добавляем уведомление в базу данных
        await conn.execute(
            f'''
            INSERT INTO {BOT_PREFIX}notifications 
                (user_id, notification_text, notification_time) 
            VALUES 
                ($1, $2, $3)
            ''',
            user_id, notification_text, notification_time
        )
        
        logger.info(f"Тестовое уведомление успешно добавлено для пользователя {user_id} на время {notification_time}")
        print(f"\n✅ Тестовое уведомление создано для пользователя {user_id}:")
        print(f"   Время уведомления: {notification_time.strftime('%d.%m.%Y %H:%M:%S %Z')}")
        print(f"   Текст: {notification_text}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении тестового уведомления: {e}")
        return False
    finally:
        if conn:
            await conn.close()
            logger.info("Соединение с PostgreSQL закрыто")

async def main():
    """
    Основная функция скрипта
    """
    # Инициализируем PostgreSQL в начале
    logger.info("Инициализация PostgreSQL...")
    postgres_initialized = await init_postgres()
    if not postgres_initialized:
        print("\n❌ Ошибка при инициализации PostgreSQL. Проверьте настройки подключения.")
        return
    
    # Проверяем наличие аргументов командной строки
    if len(sys.argv) < 2:
        print_usage()
        return

    command = sys.argv[1].lower()
    
    if command == "add":
        # Проверяем наличие обязательных аргументов
        if len(sys.argv) < 4:
            print("❌ Недостаточно аргументов для добавления пользователя.")
            print_usage()
            return
            
        chat_id = int(sys.argv[2])
        user_id = int(sys.argv[3])
        username = sys.argv[4] if len(sys.argv) > 4 else None
        
        success = await add_user_to_db(user_id, chat_id, username)
        if success:
            print(f"\n✅ Пользователь успешно добавлен в базу данных:")
            print(f"   chat_id: {chat_id}")
            print(f"   user_id: {user_id}")
            if username:
                print(f"   username: {username}")
        else:
            print("\n❌ Ошибка при добавлении пользователя в базу данных.")
            
    elif command == "list":
        print("\n📋 Получение списка пользователей из базы данных...")
        users = await get_all_users()
        
        if users:
            print(f"\n✅ Список пользователей ({len(users)}):")
            print("───────────────────────────────────────────────")
            print("  ID пользователя  │   Chat ID    │  Username")
            print("───────────────────────────────────────────────")
            for user in users:
                username = user['username'] or "N/A"
                print(f"  {user['user_id']:<15} │ {user['chat_id']:<12} │ {username}")
            print("───────────────────────────────────────────────")
        else:
            print("\n❌ Не удалось получить список пользователей или база данных пуста.")
            
    elif command == "test":
        success = await test_send_announcement()
        if success:
            print("\n✅ Тестовое объявление успешно отправлено!")
        else:
            print("\n❌ Ошибка при отправке тестового объявления.")
            
    elif command == "add_notification":
        success = await add_test_notification()
        if success:
            print("\n✅ Тестовое уведомление успешно добавлено!")
        else:
            print("\n❌ Ошибка при добавлении тестового уведомления.")
            
    else:
        print(f"❌ Неизвестная команда: {command}")
        print_usage()


def print_usage():
    """
    Выводит инструкцию по использованию скрипта
    """
    print("\nИспользование скрипта:")
    print("  python add_user_to_db.py add CHAT_ID USER_ID [USERNAME]  - добавить пользователя в базу данных")
    print("  python add_user_to_db.py list                            - вывести список всех пользователей")
    print("  python add_user_to_db.py test [CHAT_ID]                  - отправить тестовое объявление")
    print("  python add_user_to_db.py add_notification                  - добавить тестовое уведомление")
    print("\nПример:")
    print("  python add_user_to_db.py add 123456789 987654321 username")
    print("  python add_user_to_db.py list")
    print("  python add_user_to_db.py test 123456789")


if __name__ == "__main__":
    asyncio.run(main()) 