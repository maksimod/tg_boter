from imports import *
from utils import logger, chat_id, start_custom_survey
from telegram import Update

@start
def start():
    auto_write_translated_message("Привет! Я простой бот.")
    auto_message_with_buttons("Выберите действие:", [
        ["Информация", "info"],
        ["Помощь", "help"],
        ["Пройти опрос с возможностью редактирования", "start_survey"],
        ["Пройти опрос без возможности редактирования", "start_simple_survey"],
        [["Спросить ChatGPT", "ask_chatgpt"],["Выход", "exit"]],
        ["Создать уведомление", "create_notification"],
        ["Гугл", "google_test"],
        [["О боте", "about"], ["Выход", "exit"]],
        ["Создать объявление", "create_announcement"],
        ["Инициализировать базу данных", "init_database"]
    ])

@callback("google_test")
async def google_test():
    auto_write_translated_message("Тестим...")
    result = await google_sheets('1XES1siX-OZC6D0vDeElcC1kJ0ZbsEU0j4Tj3n1BzEFM')
    print(result)

@callback("info")
def info():
    auto_write_translated_message("Инфа")
    auto_button([
        ["Узнать больше", "info_more"],
        ["Вернуться в меню", "back_to_menu"]
    ])

@callback("info_more")
def info_more():
    lang = get_user_language()
    auto_write_translated_message(f"Я очень простой бот, но я могу работать на разных языках. Сейчас вы используете язык: {lang}")
    auto_button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@callback("help")
def help():
    auto_write_translated_message("Это справочное сообщение. Используйте кнопки для навигации.")
    auto_button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@callback("about")
def about():
    auto_write_translated_message("Это простой бот с удобным интерфейсом и поддержкой нескольких языков.")
    auto_button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@callback("exit")
def exit():
    auto_write_translated_message("До свидания! Для запуска бота снова используйте /start")

@callback("back_to_menu")
def back():
    start()

@callback("start_survey")
def start_demo_survey():
    survey_id = "advanced_survey"
    questions = [
        ["Как вас зовут? (Фамилия Имя)", "фио"],
        ["Сколько вам лет?", "номер:3-100"],
        ["Укажите дату встречи (ДД.ММ.ГГ, например 31.03.25 или 'сегодня', 'завтра')", "дата"],
        ["Укажите время встречи (ЧЧ:ММ)", "время"],
        ["Или укажите дату и время вместе (ДД.ММ.ГГ ЧЧ:ММ, например 31.03.25 15:30 или 'сегодня 15:30')", "дата+время"],
        ["Введите контактный телефон", "телефон"],
        ["Введите ссылку на ваш профиль (начиная с http:// или https://)", "ссылка"],
        ["Вы подтверждаете правильность введенных данных? (да/нет)", "подтверждение"],
        ["Как вы хотели бы продолжить?", [
            [["Вернуться в меню", "back_choice"]],
            [["Информация", "info_choice"], ["Помощь", "help_choice"]]
        ]]
    ]
    
    # Добавляем кнопки редактирования для каждого вопроса
    rewrite_data = [
        ["Изменить имя"],
        ["Изменить возраст"],
        ["Изменить дату встречи"],
        ["Изменить время встречи"],
        ["Изменить дату и время встречи"],
        ["Изменить телефон"],
        ["Изменить ссылку на профиль"],
        ["Изменить подтверждение"],
        ["Изменить выбор продолжения"]
    ]
    
    start_custom_survey(questions, "action", survey_id, rewrite_data=rewrite_data)

@callback("action")
def action_after_survey(answers=None, update=None, context=None):
    current_upd = update or current_update
    current_ctx = context or current_context
    
    asyncio.create_task(process_survey_results(answers, current_upd, current_ctx))

@callback("ask_chatgpt")
def ask_chatgpt_callback():
    auto_write_translated_message("Напишите ваш вопрос, и я отвечу на него с помощью ChatGPT.")
    
@chatgpt("Отвечай пользователю на английском языке")
def handle_chatgpt_message(message_text):
    pass

@callback("create_notification")
def start_notification_creation():
    auto_write_translated_message("Давайте создадим уведомление.")
    
    survey_id = "notification_survey"
    questions = [
        ["Введите дату и время уведомления (ДД.ММ.ГГ ЧЧ:ММ, например 31.03.25 16:17)", "дата+время"],
        ["Введите текст уведомления", "текст"]
    ]
    start_custom_survey(questions, "process_notification", survey_id)

@callback("process_notification")
def process_notification(answers=None, update=None, context=None):
    current_upd = update or current_update
    current_ctx = context or current_context
    
    notification_datetime = answers[0]
    notification_text = answers[1]
    create_notification(notification_datetime, notification_text, current_upd, current_ctx)

@callback("start_simple_survey")
def start_simple_survey():
    survey_id = "simple_survey"
    questions = [
        ["Как вас зовут? (Фамилия Имя)", "фио"],
        ["Сколько вам лет?", "номер:3-100"],
        ["Укажите дату встречи (ДД.ММ.ГГ, например 31.03.25 или 'сегодня', 'завтра')", "дата"],
        ["Укажите время встречи (ЧЧ:ММ)", "время"],
        ["Введите контактный телефон", "телефон"],
        ["Как вы хотели бы продолжить?", [
            [["Вернуться в меню", "back_choice"]],
            [["Информация", "info_choice"]]
        ]]
    ]
    
    # Не передаем rewrite_data, опрос будет работать по стандартной схеме
    start_custom_survey(questions, "action", survey_id)

@callback("create_announcement")
def create_announcement_callback():
    auto_write_translated_message("Давайте создадим объявление.")
    
    survey_id = "announcement_survey"
    questions = [
        ["Введите текст объявления", "текст"],
        ["Выберите получателей:", [
            [["Все пользователи", "all_recipients"]],
            [["Указать конкретных пользователей", "specific_recipients"]]
        ]]
    ]
    start_custom_survey(questions, "process_announcement", survey_id)

@callback("process_announcement")
async def process_announcement(answers=None, update=None, context=None):
    current_upd = update or current_update
    
    if answers and len(answers) >= 2:
        announcement_text = answers[0]
        recipient_choice = answers[1]
        
        # Инициализируем PostgreSQL перед отправкой объявления
        import asyncio
        import asyncpg
        from credentials.postgres.config import HOST, PORT, DATABASE, USER, PASSWORD, BOT_PREFIX
        
        # Получаем текущего пользователя и его chat_id
        current_user_id = current_upd.effective_user.id
        current_chat_id = get_chat_id_from_update(current_upd)
        
        if recipient_choice == "all_recipients":
            # Отправляем объявление всем пользователям
            auto_write_translated_message("Отправляю объявление всем пользователям...")
            
            try:
                # Добавляем текущего пользователя в базу данных
                conn = await asyncpg.connect(
                    host=HOST,
                    port=PORT,
                    user=USER,
                    password=PASSWORD,
                    database=DATABASE,
                    timeout=10.0
                )
                
                # Проверяем существование таблицы
                users_table = f"{BOT_PREFIX}users"
                table_exists = await conn.fetchval(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name=$1)",
                    users_table
                )
                
                if not table_exists:
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
                
                # Добавляем текущего пользователя в базу данных
                await conn.execute(
                    f"INSERT INTO {users_table} (user_id, chat_id, username) VALUES ($1, $2, $3) ON CONFLICT (user_id) DO UPDATE SET chat_id = $2, username = $3",
                    current_user_id, current_chat_id, current_upd.effective_user.username
                )
                
                # Закрываем соединение
                await conn.close()
                
                # Отправляем объявление ВСЕМ пользователям
                success = await announce(announcement_text, "all")
                
                if success:
                    auto_write_translated_message(f"✅ Объявление успешно отправлено всем пользователям!\n\nТекст объявления: {announcement_text}")
                else:
                    auto_write_translated_message("❌ Ошибка при отправке объявления.")
                
            except Exception as e:
                logger.error(f"Ошибка при отправке объявления: {e}")
                auto_write_translated_message(f"❌ Ошибка: {str(e)}")
            
            # Добавляем кнопку для возврата в меню
            auto_button([
                ["Вернуться в меню", "back_to_menu"]
            ])
        elif recipient_choice == "specific_recipients":
            # Запрашиваем конкретные ID пользователей
            auto_write_translated_message("Введите ID пользователей через запятую (например: 123456789, 987654321)")
            
            # Настраиваем обработчик сообщений для получения списка ID
            @on_auto_text_message
            async def handle_user_ids(message_text):
                try:
                    # Парсим список ID через запятую
                    user_ids = [int(user_id.strip()) for user_id in message_text.split(',')]
                    
                    if not user_ids:
                        auto_write_translated_message("Не указаны ID пользователей.")
                        return
                    
                    # Отправляем объявление
                    auto_write_translated_message("Отправляю объявление...")
                    try:
                        success = await announce(announcement_text, user_ids)
                        if success:
                            auto_write_translated_message(f"Объявление отправлено {len(user_ids)} пользователям.")
                        else:
                            auto_write_translated_message("Ошибка при отправке объявления.")
                    except Exception as e:
                        logger.error(f"Ошибка при отправке объявления: {e}")
                        auto_write_translated_message(f"Ошибка: {str(e)}")
                except ValueError:
                    auto_write_translated_message("Неверный формат ID. Используйте только числа, разделённые запятыми.")
                
                # Возвращаемся в меню
                auto_button([
                    ["Вернуться в меню", "back_to_menu"]
                ])
    
    # Возвращаемся в главное меню
    auto_button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@callback("init_database")
async def init_database():
    # Инициализируем базу данных
    auto_write_translated_message("⚙️ Инициализация базы данных...")
    
    # Импортируем необходимые модули
    try:
        import asyncpg
        from credentials.postgres.config import HOST, PORT, DATABASE, USER, PASSWORD, BOT_PREFIX
        
        # Устанавливаем соединение
        conn = await asyncpg.connect(
            host=HOST,
            port=PORT,
            user=USER,
            password=PASSWORD,
            database=DATABASE,
            timeout=10.0
        )
        
        # Создаем необходимые таблицы
        users_table = f"{BOT_PREFIX}users"
        notifications_table = f"{BOT_PREFIX}notifications"
        
        # Таблица пользователей
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
        
        # Таблица уведомлений с правильной структурой
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
            await conn.execute(f'''
                ALTER TABLE {notifications_table}
                ADD COLUMN notification_text TEXT
            ''')
        
        await conn.close()
        auto_write_translated_message("✅ База данных успешно инициализирована!")
        
    except Exception as e:
        auto_write_translated_message(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    from base.bot_init import initialize_bot
    from easy_bot import run_bot, get_bot_instance
    import asyncio
    import sys
    from telegram import Update
    
    # Для Windows используем специальный подход для асинхронного запуска
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    # Создаем новый event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Инициализируем базу данных при запуске
        import asyncpg
        from credentials.postgres.config import HOST, PORT, DATABASE, USER, PASSWORD, BOT_PREFIX
        
        async def init_db():
            print("Инициализация базы данных при запуске бота...")
            conn = None
            try:
                # Устанавливаем соединение
                conn = await asyncpg.connect(
                    host=HOST,
                    port=PORT,
                    user=USER,
                    password=PASSWORD,
                    database=DATABASE,
                    timeout=10.0
                )
                
                # Создаем необходимые таблицы
                users_table = f"{BOT_PREFIX}users"
                notifications_table = f"{BOT_PREFIX}notifications"
                
                # Таблица пользователей
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
                
                # Таблица уведомлений с правильной структурой
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
                    print(f"Добавление столбца notification_text в таблицу {notifications_table}")
                    await conn.execute(f'''
                        ALTER TABLE {notifications_table}
                        ADD COLUMN notification_text TEXT
                    ''')
                    print(f"Столбец notification_text успешно добавлен")
                
                print("База данных успешно инициализирована при запуске!")
                return True
            except Exception as e:
                print(f"Ошибка при инициализации базы данных при запуске: {e}")
                return False
            finally:
                if conn:
                    await conn.close()
        
        # Выполняем инициализацию базы данных
        loop.run_until_complete(init_db())
        
        # Инициализируем и запускаем бота (в том же event loop)
        app = initialize_bot()
        if app:
            print("Бот инициализирован, запускаем...")
            # Запускаем бота в том же event loop
            app.run_polling(allowed_updates=Update.ALL_TYPES)
        else:
            print("Ошибка: бот не был инициализирован")
    except Exception as e:
        print(f"Критическая ошибка при запуске: {e}")
    finally:
        # Закрываем event loop при выходе
        loop.close()