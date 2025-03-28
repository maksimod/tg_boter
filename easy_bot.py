import logging
import os
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Импортируем функцию перевода
try:
    from language.translate_any_message import translate_any_message
    print("Translation module imported successfully")
except ImportError as e:
    print(f"Error importing translation module: {e}")
    translate_any_message = None

# Импортируем PostgreSQL
try:
    import asyncpg
    import asyncio
    from asyncio import Lock
    print("PostgreSQL module imported successfully")
except ImportError as e:
    print(f"Error importing PostgreSQL module: {e}")
    print("Installing asyncpg...")
    os.system("pip install asyncpg")
    try:
        import asyncpg
        import asyncio
        from asyncio import Lock
        print("PostgreSQL module installed successfully")
    except ImportError:
        print("Failed to install asyncpg. Please install it manually: pip install asyncpg")
        asyncpg = None

# Настройки бота
BOT_TOKEN = ""  # Будет загружен из файла конфигурации
TIMEOUT = 30

# Глобальные переменные
callbacks = {}
current_update = None
current_context = None

# PostgreSQL настройки
DB_HOST = None
DB_PORT = None
DB_NAME = None
DB_USER = None 
DB_PASSWORD = None
BOT_PREFIX = "tgbot_"  # Префикс по умолчанию
db_lock = Lock()  # Блокировка для DB-операций
db_initialized = False  # Флаг инициализации БД

# Настройки языков
LANGUAGES = {
    "ru": "Русский",
    "en": "English",
    "uk": "Українська",
    "zh": "中文",
    "es": "Español",
    "fr": "Français",
}

# Словарь перевода сообщений
TRANSLATIONS = {
    "ru": {},  # Русские сообщения (заполняется автоматически)
    "en": {},  # Английские сообщения будут переведены
    "uk": {},  # Украинские сообщения будут переведены
    "zh": {},  # Китайские сообщения будут переведены
    "es": {},  # Испанские сообщения будут переведены
    "fr": {},  # Французские сообщения будут переведены
}

# Состояния пользователя для создания напоминания
NOTIFICATION_TEXT = 1
NOTIFICATION_DATE = 2
NOTIFICATION_TIME = 3

# Словарь текущих состояний создания напоминаний пользователей
notification_states = {}

# Функция для добавления callback
def add_callback(callback_name, func):
    callbacks[callback_name] = func

# Текущий язык пользователя
def get_user_language():
    """Получить текущий язык пользователя из контекста"""
    if current_context and hasattr(current_context, 'user_data') and 'language' in current_context.user_data:
        return current_context.user_data['language']
    return "ru"  # По умолчанию русский

def set_user_language(lang_code):
    """Установить язык пользователя"""
    if current_context and hasattr(current_context, 'user_data'):
        current_context.user_data['language'] = lang_code

# Загрузка токена из файла конфигурации
def load_token():
    """Загружает токен бота из файла конфигурации"""
    global BOT_TOKEN
    try:
        # Проверяем наличие папки credentials
        if os.path.exists("credentials/telegram"):
            # Пытаемся импортировать из модуля
            try:
                from credentials.telegram.config import BOT_TOKEN as TOKEN
                BOT_TOKEN = TOKEN
                print("Токен загружен из credentials/telegram/config.py")
                return True
            except ImportError:
                pass
            
            # Пытаемся прочитать из файла
            try:
                token_path = "credentials/telegram/token.txt"
                if os.path.exists(token_path):
                    with open(token_path, "r") as f:
                        BOT_TOKEN = f.read().strip()
                    print("Токен загружен из credentials/telegram/token.txt")
                    return True
            except Exception:
                pass
    except Exception as e:
        print(f"Ошибка при загрузке токена: {e}")
    
    return False

# Загрузка настроек PostgreSQL
def load_postgres_config():
    """Загружает настройки подключения к PostgreSQL из файла конфигурации"""
    global BOT_PREFIX, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
    
    try:
        # Проверяем наличие папки credentials/postgres
        if os.path.exists("credentials/postgres"):
            try:
                from credentials.postgres.config import (
                    HOST, DATABASE, USER, PASSWORD, PORT, BOT_PREFIX as PREFIX
                )
                DB_HOST = HOST
                DB_PORT = PORT
                DB_NAME = DATABASE
                DB_USER = USER
                DB_PASSWORD = PASSWORD
                BOT_PREFIX = PREFIX if PREFIX else BOT_PREFIX
                print(f"Настройки PostgreSQL загружены из config.py. BOT_PREFIX: {BOT_PREFIX}")
                return True
            except ImportError:
                print("Не удалось загрузить настройки PostgreSQL из модуля")
            except Exception as e:
                print(f"Ошибка при загрузке настроек PostgreSQL: {e}")
                
    except Exception as e:
        print(f"Ошибка при загрузке настроек PostgreSQL: {e}")
    
    print("Не удалось загрузить настройки PostgreSQL")
    return False

# Функция для создания нового соединения с БД
async def get_db_connection():
    """Создает новое соединение с базой данных"""
    if asyncpg is None:
        print("PostgreSQL не доступен - модуль asyncpg не установлен")
        return None
    
    if None in (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD):
        print("Настройки PostgreSQL не загружены")
        return None
        
    try:
        # Создаем новое соединение для каждой операции
        connection = await asyncpg.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            timeout=10.0,
            command_timeout=10.0,
            ssl=False
        )
        return connection
    except Exception as e:
        print(f"Ошибка при создании соединения с БД: {e}")
        return None

# Инициализация PostgreSQL
async def init_postgres():
    """Инициализирует соединение с PostgreSQL и создает таблицы"""
    global db_initialized
    
    if asyncpg is None:
        print("PostgreSQL не доступен - модуль asyncpg не установлен")
        return False
    
    # Загружаем конфигурацию
    if not load_postgres_config():
        print("Не удалось загрузить настройки PostgreSQL")
        return False
    
    try:
        print(f"Подключение к PostgreSQL: {DB_HOST}:{DB_PORT}, DB: {DB_NAME}, User: {DB_USER}")
        
        # Проверяем соединение
        connection = await get_db_connection()
        if connection is None:
            print("Не удалось создать соединение с PostgreSQL")
            return False
            
        try:
            # Проверяем соединение
            await connection.execute("SELECT 1")
            print("Соединение с PostgreSQL успешно установлено")
            
            # Создаем таблицы
            db_initialized = await create_tables(connection)
            
            return db_initialized
        finally:
            # Закрываем соединение в любом случае
            await connection.close()
            
    except Exception as e:
        print(f"Ошибка при инициализации PostgreSQL: {e}")
        return False

# Создание таблиц
async def create_tables(connection=None):
    """Создает необходимые таблицы в базе данных"""
    if asyncpg is None:
        print("PostgreSQL не доступен - модуль asyncpg не установлен")
        return False
    
    # Если соединение не передано, создаем новое
    close_conn = False
    if connection is None:
        connection = await get_db_connection()
        close_conn = True
        
    if connection is None:
        print("Не удалось создать соединение с PostgreSQL")
        return False
    
    try:
        # Таблица пользователей
        await connection.execute(f'''
            CREATE TABLE IF NOT EXISTS {BOT_PREFIX}users (
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
            CREATE TABLE IF NOT EXISTS {BOT_PREFIX}messages (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES {BOT_PREFIX}users(id),
                message_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица переводов
        await connection.execute(f'''
            CREATE TABLE IF NOT EXISTS {BOT_PREFIX}translations (
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
            CREATE TABLE IF NOT EXISTS {BOT_PREFIX}notifications (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES {BOT_PREFIX}users(id),
                notification_text TEXT NOT NULL,
                notification_time TIME NOT NULL,
                notification_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_sent BOOLEAN DEFAULT FALSE,
                is_deleted BOOLEAN DEFAULT FALSE
            )
        ''')
        
        print(f"Таблицы с префиксом '{BOT_PREFIX}' созданы")
        
        return True
    except Exception as e:
        print(f"Ошибка при создании таблиц: {e}")
        return False
    finally:
        # Если мы создали соединение внутри этой функции, закрываем его
        if close_conn and connection is not None:
            await connection.close()

# Добавление пользователя в БД
async def add_user_to_db(user_id, chat_id, username):
    """Добавляет пользователя в базу данных"""
    if not db_initialized:
        print("PostgreSQL не инициализирован")
        return None
    
    max_retries = 3
    for attempt in range(max_retries):
        connection = None
        try:
            async with db_lock:
                # Создаем новое соединение
                connection = await get_db_connection()
                if connection is None:
                    if attempt < max_retries - 1:
                        print("Не удалось создать соединение, пробуем снова...")
                        await asyncio.sleep(1)
                        continue
                    else:
                        print("Не удалось создать соединение после всех попыток")
                        return None
                
                # Проверяем, существует ли пользователь
                user = await connection.fetchrow(
                    f"SELECT id FROM {BOT_PREFIX}users WHERE user_id = $1",
                    user_id
                )
                
                if user:
                    print(f"Пользователь {user_id} уже существует в БД")
                    return user['id']
                
                # Добавляем нового пользователя
                user_id_in_db = await connection.fetchval(
                    f'''
                    INSERT INTO {BOT_PREFIX}users (user_id, chat_id, username)
                    VALUES ($1, $2, $3)
                    RETURNING id
                    ''',
                    user_id, chat_id, username
                )
                
                print(f"Добавлен новый пользователь: {username} (ID: {user_id})")
                return user_id_in_db
                
        except Exception as e:
            print(f"Ошибка при добавлении пользователя (попытка {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print("Повторная попытка через 1 секунду...")
                await asyncio.sleep(1)
            else:
                return None
        finally:
            # Закрываем соединение в любом случае
            if connection:
                await connection.close()
    
    return None

# Добавление сообщения в БД
async def add_message_to_db(user_db_id, message_text):
    """Добавляет сообщение в базу данных"""
    if not db_initialized:
        print("PostgreSQL не инициализирован")
        return False
    
    max_retries = 3
    for attempt in range(max_retries):
        connection = None
        try:
            async with db_lock:
                # Создаем новое соединение
                connection = await get_db_connection()
                if connection is None:
                    if attempt < max_retries - 1:
                        print("Не удалось создать соединение, пробуем снова...")
                        await asyncio.sleep(1)
                        continue
                    else:
                        print("Не удалось создать соединение после всех попыток")
                        return False
                
                await connection.execute(
                    f'''
                    INSERT INTO {BOT_PREFIX}messages (user_id, message_text)
                    VALUES ($1, $2)
                    ''',
                    user_db_id, message_text
                )
                
                return True
                
        except Exception as e:
            print(f"Ошибка при добавлении сообщения (попытка {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print("Повторная попытка через 1 секунду...")
                await asyncio.sleep(1)
            else:
                return False
        finally:
            # Закрываем соединение в любом случае
            if connection:
                await connection.close()
    
    return False

# Получение перевода из БД
async def get_translation_from_db(source_text, target_language):
    """Получает перевод из базы данных"""
    if not db_initialized:
        print("PostgreSQL не инициализирован")
        return None
    
    max_retries = 3
    for attempt in range(max_retries):
        connection = None
        try:
            async with db_lock:
                # Создаем новое соединение
                connection = await get_db_connection()
                if connection is None:
                    if attempt < max_retries - 1:
                        print("Не удалось создать соединение, пробуем снова...")
                        await asyncio.sleep(1)
                        continue
                    else:
                        print("Не удалось создать соединение после всех попыток")
                        return None
                
                result = await connection.fetchrow(
                    f'''
                    SELECT translated_text
                    FROM {BOT_PREFIX}translations
                    WHERE source_text = $1 AND target_language = $2
                    ORDER BY created_at DESC
                    LIMIT 1
                    ''',
                    source_text, target_language
                )
                
                if result:
                    return result['translated_text']
                else:
                    return None
                
        except Exception as e:
            print(f"Ошибка при получении перевода (попытка {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print("Повторная попытка через 1 секунду...")
                await asyncio.sleep(1)
            else:
                return None
        finally:
            # Закрываем соединение в любом случае
            if connection:
                await connection.close()
    
    return None

# Сохранение перевода в БД
async def save_translation_to_db(source_text, translated_text, source_language, target_language):
    """Сохраняет перевод в базу данных"""
    if not db_initialized:
        print("PostgreSQL не инициализирован")
        return False
    
    max_retries = 3
    for attempt in range(max_retries):
        connection = None
        try:
            async with db_lock:
                # Создаем новое соединение
                connection = await get_db_connection()
                if connection is None:
                    if attempt < max_retries - 1:
                        print("Не удалось создать соединение, пробуем снова...")
                        await asyncio.sleep(1)
                        continue
                    else:
                        print("Не удалось создать соединение после всех попыток")
                        return False
                
                # Проверяем, существует ли уже такой перевод
                existing = await connection.fetchval(
                    f'''
                    SELECT COUNT(*)
                    FROM {BOT_PREFIX}translations
                    WHERE source_text = $1 AND target_language = $2
                    ''',
                    source_text, target_language
                )
                
                if existing > 0:
                    # Обновляем существующий перевод
                    await connection.execute(
                        f'''
                        UPDATE {BOT_PREFIX}translations
                        SET translated_text = $1, created_at = CURRENT_TIMESTAMP
                        WHERE source_text = $2 AND target_language = $3
                        ''',
                        translated_text, source_text, target_language
                    )
                else:
                    # Добавляем новый перевод
                    await connection.execute(
                        f'''
                        INSERT INTO {BOT_PREFIX}translations 
                        (source_text, translated_text, source_language, target_language)
                        VALUES ($1, $2, $3, $4)
                        ''',
                        source_text, translated_text, source_language, target_language
                    )
                
                return True
                
        except Exception as e:
            print(f"Ошибка при сохранении перевода (попытка {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print("Повторная попытка через 1 секунду...")
                await asyncio.sleep(1)
            else:
                return False
        finally:
            # Закрываем соединение в любом случае
            if connection:
                await connection.close()
    
    return False

# Функция для отправки сообщения
async def write_message(text):
    """Простая функция для отправки сообщения"""
    if current_update and current_context:
        if current_update.callback_query:
            await current_update.callback_query.edit_message_text(text=text)
        else:
            await current_update.message.reply_text(text=text)

# Функция для перевода сообщения
async def translate(text, target_lang=None):
    """Возвращает перевод сообщения на указанный язык"""
    if target_lang is None:
        target_lang = get_user_language()
    
    # Получаем полное название языка
    target_language = LANGUAGES.get(target_lang, "English")
    
    # Если запрошен русский язык или функция перевода недоступна
    if target_lang == "ru" or not translate_any_message:
        return text
    
    # Максимальное количество попыток для перевода
    max_retries = 3
    
    # Для коротких текстов не используем кэширование
    use_cache = len(text) > 10
    
    for attempt in range(max_retries):
        try:
            # Проверяем кэш переводов в БД
            cached_translation = None
            if use_cache and db_initialized:
                try:
                    cached_translation = await get_translation_from_db(text, target_language)
                except Exception as cache_error:
                    logging.warning(f"Ошибка при получении кэша перевода: {cache_error}")
            
            if cached_translation:
                logging.info(f"Используем кэшированный перевод для: {text[:20]}...")
                return cached_translation
            
            # Используем функцию перевода из старого бота
            try:
                translated_text = await translate_any_message(
                    text,
                    target_language,
                    source_language="Russian",
                    on_translate_start=None,
                    on_translate_end=None
                )
                
                # Сохраняем перевод в БД, если успешно
                if translated_text and translated_text != text and use_cache and db_initialized:
                    try:
                        await save_translation_to_db(text, translated_text, "Russian", target_language)
                    except Exception as save_error:
                        # Ошибка при сохранении не должна прерывать работу бота
                        logging.error(f"Ошибка при сохранении перевода в БД: {save_error}")
                
                return translated_text
            except Exception as translate_error:
                logging.error(f"Ошибка при переводе (попытка {attempt+1}/{max_retries}): {translate_error}")
                if attempt < max_retries - 1:
                    logging.info("Повторная попытка перевода через 1 секунду...")
                    await asyncio.sleep(1)  # Пауза перед повторной попыткой
                else:
                    logging.error("Все попытки перевода исчерпаны, возвращаем исходный текст")
                    return text
                
        except Exception as general_error:
            logging.error(f"Общая ошибка при переводе (попытка {attempt+1}/{max_retries}): {general_error}")
            if attempt < max_retries - 1:
                logging.info("Повторная попытка через 1 секунду...")
                await asyncio.sleep(1)  # Пауза перед повторной попыткой
            else:
                # В случае ошибки возвращаем исходный текст
                return text
    
    # В случае всех неудачных попыток возвращаем исходный текст
    return text

# Функция для отправки переведенного сообщения
async def write_translated_message(text):
    """Отправляет сообщение, переведенное на язык пользователя"""
    translated_text = await translate(text)
    await write_message(translated_text)

# Функция для создания кнопок
async def button(buttons_layout):
    """Создает кнопки из простого списка"""
    keyboard = []
    
    for row in buttons_layout:
        if isinstance(row[0], list):
            # Это строка с несколькими кнопками
            keyboard_row = []
            for btn in row:
                # Переводим текст кнопки
                btn_text = await translate(btn[0])
                keyboard_row.append(InlineKeyboardButton(btn_text, callback_data=btn[1]))
            keyboard.append(keyboard_row)
        else:
            # Это одна кнопка в строке
            btn_text = await translate(row[0])
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=row[1])])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if current_update and current_context:
        if current_update.callback_query:
            await current_update.callback_query.edit_message_reply_markup(reply_markup=reply_markup)
        else:
            # Переводим текст-подсказку
            prompt = await translate("Выберите опцию:")
            await current_update.message.reply_text(
                text=prompt,
                reply_markup=reply_markup
            )

# Функция для отправки сообщения с кнопками
async def message_with_buttons(text, buttons_layout):
    """Отправляет сообщение с кнопками"""
    keyboard = []
    
    for row in buttons_layout:
        if isinstance(row[0], list):
            # Это строка с несколькими кнопками
            keyboard_row = []
            for btn in row:
                # Переводим текст кнопки
                btn_text = await translate(btn[0])
                keyboard_row.append(InlineKeyboardButton(btn_text, callback_data=btn[1]))
            keyboard.append(keyboard_row)
        else:
            # Это одна кнопка в строке
            btn_text = await translate(row[0])
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=row[1])])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Переводим текст сообщения
    translated_text = await translate(text)
    
    if current_update and current_context:
        if current_update.callback_query:
            await current_update.callback_query.edit_message_text(
                text=translated_text,
                reply_markup=reply_markup
            )
        else:
            await current_update.message.reply_text(
                text=translated_text,
                reply_markup=reply_markup
            )

# Создание клавиатуры выбора языка
def create_language_keyboard():
    """Создает клавиатуру выбора языка"""
    keyboard = []
    row = []
    
    for lang_code, lang_name in LANGUAGES.items():
        if len(row) == 2:
            keyboard.append(row)
            row = []
        row.append(InlineKeyboardButton(lang_name, callback_data=f"lang_{lang_code}"))
    
    if row:
        keyboard.append(row)
    
    return InlineKeyboardMarkup(keyboard)

# Показать выбор языка
async def show_language_selection():
    """Показывает меню выбора языка"""
    if current_update and current_context:
        # Многоязычное сообщение
        welcome_message = "Выберите язык / Choose language / Виберіть мову / 选择语言 / Seleccione idioma / Choisissez la langue"
        
        if current_update.callback_query:
            await current_update.callback_query.edit_message_text(
                text=welcome_message,
                reply_markup=create_language_keyboard()
            )
        else:
            await current_update.message.reply_text(
                text=welcome_message,
                reply_markup=create_language_keyboard()
            )

# Получение callback_data
def get_callback():
    """Возвращает callback_data текущего обновления"""
    if current_update and current_update.callback_query:
        return current_update.callback_query.data
    return None

# Декоратор для безопасного выполнения функций напоминаний
def safe_notification_handler(func):
    """Декоратор для обработки ошибок в функциях напоминаний"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        global current_update, current_context
        try:
            # Проверяем, что context не None
            if context is None or update is None:
                print("Ошибка: context или update равны None")
                if update:
                    # Используем функцию показа ошибки
                    await show_error_with_menu_button("Произошла ошибка. Пожалуйста, попробуйте снова.", update, context)
                return
            
            # Сохраняем контекст и обновление
            current_update = update
            current_context = context
            
            # Вызываем оригинальную функцию
            return await func(update, context)
        except Exception as e:
            print(f"Ошибка при выполнении {func.__name__}: {e}")
            import traceback
            traceback.print_exc()
            
            try:
                # Отправляем сообщение об ошибке с кнопкой возврата в меню
                if update and hasattr(update, 'effective_chat'):
                    await show_error_with_menu_button("Произошла ошибка. Пожалуйста, попробуйте позже.", update, context)
            except Exception as msg_error:
                print(f"Ошибка при отправке сообщения об ошибке: {msg_error}")
    
    return wrapper

# Функция для показа сообщения об ошибке с кнопкой возврата в меню
async def show_error_with_menu_button(error_message="Произошла ошибка. Пожалуйста, попробуйте позже.", update=None, context=None):
    """Показывает сообщение об ошибке с кнопкой возврата в меню"""
    try:
        # Определяем, откуда пришел запрос - из глобальных переменных или из параметров
        update_obj = update or current_update
        
        if not update_obj:
            print("Ошибка: update не доступен")
            return
            
        # Создаем кнопку возврата в меню
        reply_markup = InlineKeyboardMarkup([[
            InlineKeyboardButton("Вернуться в главное меню", callback_data="back_to_main")
        ]])
        
        # Переводим сообщение об ошибке
        translated_text = await translate(error_message)
        
        # Отправляем сообщение
        if update_obj.callback_query:
            await update_obj.callback_query.edit_message_text(
                text=translated_text,
                reply_markup=reply_markup
            )
        elif hasattr(update_obj, 'message') and update_obj.message:
            await update_obj.message.reply_text(
                text=translated_text,
                reply_markup=reply_markup
            )
    except Exception as e:
        print(f"Ошибка при показе сообщения об ошибке: {e}")
        import traceback
        traceback.print_exc()

# Обработчик команды старт
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_update, current_context
    current_update = update
    current_context = context
    
    # Добавляем пользователя в БД
    user = update.effective_user
    chat_id = update.effective_chat.id
    user_db_id = await add_user_to_db(user.id, chat_id, user.username)
    
    # Сохраняем id пользователя в БД в контексте
    if user_db_id:
        context.user_data['db_user_id'] = user_db_id
    
    # Если у пользователя нет выбранного языка, показываем выбор языка
    if 'language' not in context.user_data:
        await show_language_selection()
        return
    
    # Запускаем пользовательскую функцию
    if 'start' in callbacks:
        await callbacks['start']()
    else:
        await write_translated_message("Привет! Я бот. Используйте /help для помощи.")

# Обработчик обычных сообщений
@safe_notification_handler
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_update, current_context
    current_update = update
    current_context = context
    
    # Получаем id пользователя в БД
    user_db_id = context.user_data.get('db_user_id')
    
    # Если пользователь еще не в БД, добавляем его
    if not user_db_id:
        user = update.effective_user
        chat_id = update.effective_chat.id
        user_db_id = await add_user_to_db(user.id, chat_id, user.username)
        context.user_data['db_user_id'] = user_db_id
    
    # Сохраняем сообщение в БД
    if user_db_id:
        await add_message_to_db(user_db_id, update.message.text)
    
    # Если у пользователя нет выбранного языка, показываем выбор языка
    if 'language' not in context.user_data:
        await show_language_selection()
        return
    
    # Проверяем, находится ли пользователь в процессе создания напоминания
    user_id = update.effective_user.id
    if user_id in notification_states:
        await process_notification_creation(update, context, user_id, user_db_id)
        return
    
    # Если есть обработчик для текстовых сообщений, вызываем его
    if 'text_message' in callbacks:
        await callbacks['text_message'](update.message.text)
    else:
        # По умолчанию просто отвечаем эхом
        await write_translated_message(f"Вы написали: {update.message.text}")

# Обработчик callback запросов
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_update, current_context
    
    print(f"Получен callback запрос: {update.callback_query.data}")
    
    current_update = update
    current_context = context
    
    callback_data = update.callback_query.data
    
    # Проверяем, не выбор ли это языка
    if callback_data.startswith("lang_"):
        lang_code = callback_data.replace("lang_", "")
        # Сохраняем выбранный язык
        context.user_data['language'] = lang_code
        
        # Сообщаем о выбранном языке
        lang_name = LANGUAGES.get(lang_code, "Unknown")
        await update.callback_query.answer(f"Выбран язык: {lang_name}")
        
        # Запускаем стартовую функцию
        if 'start' in callbacks:
            await callbacks['start']()
        else:
            await write_translated_message("Привет! Я бот. Используйте /help для помощи.")
        return
    
    # Запускаем соответствующий обработчик callback
    if callback_data in callbacks:
        print(f"Запуск обработчика для {callback_data}")
        await callbacks[callback_data]()
    else:
        print(f"Обработчик для {callback_data} не найден")
        await update.callback_query.answer(text=f"Обработчик для {callback_data} не найден")

# Функция для регистрации обработчика команды /start
def on_start(func):
    """Регистрирует функцию как обработчик команды /start"""
    callbacks['start'] = func
    return func

# Функция для регистрации обработчика callback
def on_callback(callback_data):
    """Декоратор для регистрации функции как обработчика callback"""
    def decorator(func):
        callbacks[callback_data] = func
        return func
    return decorator

# Функция для регистрации обработчика текстовых сообщений
def on_text_message(func):
    """Регистрирует функцию как обработчик текстовых сообщений"""
    callbacks['text_message'] = func
    return func

# Функция для инициализации БД
async def setup_db():
    """Инициализирует базу данных"""
    return await init_postgres()

# Удаление пользователя и всех его сообщений из БД
async def delete_user_data(user_id):
    """Удаляет пользователя и все его сообщения из базы данных"""
    if not db_initialized:
        print("PostgreSQL не инициализирован")
        return False
    
    max_retries = 3
    for attempt in range(max_retries):
        connection = None
        try:
            async with db_lock:
                # Создаем новое соединение
                connection = await get_db_connection()
                if connection is None:
                    if attempt < max_retries - 1:
                        print("Не удалось создать соединение, пробуем снова...")
                        await asyncio.sleep(1)
                        continue
                    else:
                        print("Не удалось создать соединение после всех попыток")
                        return False
                
                # Находим ID пользователя в БД
                db_user_id = await connection.fetchval(
                    f"SELECT id FROM {BOT_PREFIX}users WHERE user_id = $1",
                    user_id
                )
                
                if not db_user_id:
                    print(f"Пользователь {user_id} не найден в БД")
                    return False
                
                # Начинаем транзакцию для последовательного удаления
                async with connection.transaction():
                    # Удаляем все сообщения пользователя
                    await connection.execute(
                        f"DELETE FROM {BOT_PREFIX}messages WHERE user_id = $1",
                        db_user_id
                    )
                    
                    print(f"Удалены все сообщения пользователя {user_id}")
                    
                    # Удаляем самого пользователя
                    await connection.execute(
                        f"DELETE FROM {BOT_PREFIX}users WHERE id = $1",
                        db_user_id
                    )
                    
                    print(f"Пользователь {user_id} удален из БД")
                
                return True
                
        except Exception as e:
            print(f"Ошибка при удалении пользователя (попытка {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print("Повторная попытка через 1 секунду...")
                await asyncio.sleep(1)
            else:
                return False
        finally:
            # Закрываем соединение в любом случае
            if connection:
                await connection.close()
    
    return False

# Обработчик ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ошибки телеграм API"""
    try:
        if update.effective_user:
            user_id = update.effective_user.id
            error = context.error
            error_str = str(error).lower()
            
            # Проверяем, заблокировал ли пользователь бота
            if 'forbidden' in error_str or 'bot was blocked' in error_str or 'chat not found' in error_str:
                print(f"Пользователь {user_id} заблокировал бота. Удаляем его данные из БД.")
                await delete_user_data(user_id)
                
                # Удаляем пользовательские данные из контекста
                if hasattr(context, 'user_data'):
                    context.user_data.clear()
            
            # Логируем ошибку
            logging.error(f"Ошибка для пользователя {user_id}: {error}")
        else:
            logging.error(f"Произошла ошибка: {context.error}")
    except Exception as e:
        logging.error(f"Ошибка в обработчике ошибок: {e}")

# Обработчик команды /reload_bot
async def reload_bot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Перезапускает бота для пользователя, начиная с выбора языка"""
    global current_update, current_context
    current_update = update
    current_context = context
    
    user = update.effective_user
    
    # Очищаем данные о пользователе в контексте
    if 'language' in context.user_data:
        del context.user_data['language']
    
    # Приветственное сообщение
    await update.message.reply_text(
        "OK"
    )
    
    # Показываем выбор языка
    await show_language_selection()

# Обработчик команды /check_notifications
@safe_notification_handler
async def check_notifications_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверяет напоминания для текущего пользователя и отправляет те, 
    которые уже должны быть отправлены"""
    global current_update, current_context
    current_update = update
    current_context = context
    
    # Получаем текущую дату и время
    now = datetime.now()
    current_date = now.date()
    current_time = now.time()
    
    # Проверяем и отправляем напоминания
    notifications = await get_active_notifications(current_date, current_time)
    
    if not notifications:
        await show_not_found_with_menu_button(update, context)
        return
    
    # Отправляем напоминания
    for notification in notifications:
        # Форматируем сообщение
        time_str = notification['time'].strftime('%H:%M')
        date_str = notification['date'].strftime('%d.%m.%Y')
        
        message = f"🔔 *НАПОМИНАНИЕ*: {notification['text']}\n\n"
        message += f"📅 Дата: {date_str}\n"
        message += f"⏰ Время: {time_str}"
        
        # Отправляем сообщение
        await context.bot.send_message(
            chat_id=notification['chat_id'],
            text=message,
            parse_mode='Markdown'
        )
        
        # Помечаем напоминание как отправленное
        await mark_notification_as_sent(notification['id'])
    
    # Создаем кнопку возврата в меню
    keyboard = [[InlineKeyboardButton("◀️ Вернуться в главное меню", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем сообщение
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text="Проверка напоминаний завершена. Отправлены все активные напоминания.",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            text="Проверка напоминаний завершена. Отправлены все активные напоминания.",
            reply_markup=reply_markup
        )

# Создание напоминания - начало процесса
@safe_notification_handler
async def create_notification_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начинает процесс создания нового напоминания"""
    global current_update, current_context
    current_update = update
    current_context = context
    
    user_id = update.effective_user.id
    
    # Установка состояния - ожидаем ввод текста напоминания
    notification_states[user_id] = {
        'state': NOTIFICATION_TEXT
    }
    
    # Переводим и отправляем сообщение
    await write_translated_message("Введите текст напоминания:")

# Обработчик команды показа напоминаний
@safe_notification_handler
async def list_notifications_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список напоминаний пользователя"""
    global current_update, current_context
    current_update = update
    current_context = context
    
    # Получаем id пользователя в БД
    user_db_id = context.user_data.get('db_user_id')
    if not user_db_id:
        await show_not_found_with_menu_button(update, context)
        return
    
    # Получаем список напоминаний
    notifications = await get_user_notifications(user_db_id)
    
    if not notifications:
        await show_not_found_with_menu_button(update, context)
        return
    
    # Формируем сообщение со списком напоминаний
    message = "Ваши напоминания:\n\n"
    
    for i, notification in enumerate(notifications, 1):
        date_str = notification['date'].strftime('%d.%m.%Y')
        time_str = notification['time'].strftime('%H:%M')
        message += f"{i}. {date_str} в {time_str}: {notification['text']}\n"
    
    # Добавляем инструкцию по удалению
    message += "\nДля удаления напоминания используйте команду /delete_notification [номер]"
    
    # Создаем кнопку возврата в меню
    keyboard = [[InlineKeyboardButton("◀️ Вернуться в главное меню", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем сообщение
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text=message,
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            text=message,
            reply_markup=reply_markup
        )

# Обработчик команды удаления напоминания
@safe_notification_handler
async def delete_notification_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаляет напоминание пользователя"""
    global current_update, current_context
    current_update = update
    current_context = context
    
    # Получаем id пользователя в БД
    user_db_id = context.user_data.get('db_user_id')
    if not user_db_id:
        await show_not_found_with_menu_button(update, context)
        return
    
    # Проверяем, указан ли номер напоминания
    if not context.args or not context.args[0].isdigit():
        # Создаем кнопку возврата в меню
        keyboard = [[InlineKeyboardButton("◀️ Вернуться в главное меню", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем сообщение
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text="Укажите номер напоминания для удаления. Например: /delete_notification 1",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                text="Укажите номер напоминания для удаления. Например: /delete_notification 1",
                reply_markup=reply_markup
            )
        return
    
    # Получаем номер напоминания
    notification_num = int(context.args[0])
    
    # Получаем список напоминаний
    notifications = await get_user_notifications(user_db_id)
    
    if not notifications:
        await show_not_found_with_menu_button(update, context)
        return
    
    # Проверяем, существует ли напоминание с таким номером
    if notification_num < 1 or notification_num > len(notifications):
        # Создаем кнопку возврата в меню
        keyboard = [[InlineKeyboardButton("◀️ Вернуться в главное меню", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем сообщение
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=f"Напоминание с номером {notification_num} не найдено.",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                text=f"Напоминание с номером {notification_num} не найдено.",
                reply_markup=reply_markup
            )
        return
    
    # Получаем ID напоминания
    notification_id = notifications[notification_num - 1]['id']
    
    # Удаляем напоминание
    result = await delete_notification(notification_id)
    
    if result:
        # Создаем кнопку возврата в меню
        keyboard = [[InlineKeyboardButton("◀️ Вернуться в главное меню", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем сообщение
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text=f"Напоминание номер {notification_num} успешно удалено.",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                text=f"Напоминание номер {notification_num} успешно удалено.",
                reply_markup=reply_markup
            )
    else:
        await show_error_with_menu_button("Не удалось удалить напоминание. Пожалуйста, попробуйте позже.", update, context)

# Проверка и отправка активных напоминаний
async def check_and_send_notifications(bot):
    """Проверяет и отправляет активные напоминания"""
    if not db_initialized:
        print("PostgreSQL не инициализирован, пропускаем проверку напоминаний")
        return
    
    try:
        # Получаем текущую дату и время
        now = datetime.now()
        current_date = now.date()
        current_time = now.time()
        
        print(f"Проверка напоминаний: дата {current_date}, время {current_time}")
        
        # Получаем активные напоминания
        notifications = await get_active_notifications(current_date, current_time)
        
        # Если нет активных напоминаний, выходим
        if not notifications:
            print("Активных напоминаний для отправки не найдено")
            return
        
        print(f"Найдено {len(notifications)} активных напоминаний для отправки")
        
        # Отправляем каждое напоминание
        for notification in notifications:
            try:
                # Форматируем сообщение
                time_str = notification['time'].strftime('%H:%M')
                date_str = notification['date'].strftime('%d.%m.%Y')
                
                message = f"🔔 *НАПОМИНАНИЕ*: {notification['text']}\n\n"
                message += f"📅 Дата: {date_str}\n"
                message += f"⏰ Время: {time_str}"
                
                print(f"Отправка напоминания ID {notification['id']} пользователю {notification['user_id']}, chat_id {notification['chat_id']}")
                
                # Отправляем сообщение
                await bot.send_message(
                    chat_id=notification['chat_id'],
                    text=message,
                    parse_mode='Markdown'
                )
                
                # Помечаем напоминание как отправленное
                await mark_notification_as_sent(notification['id'])
                
                print(f"Напоминание ID {notification['id']} успешно отправлено и помечено как отправленное")
                
            except Exception as e:
                print(f"Ошибка при отправке напоминания ID {notification['id']}: {e}")
    
    except Exception as e:
        print(f"Общая ошибка при проверке напоминаний: {e}")
        import traceback
        traceback.print_exc()

# Обработка создания напоминания
async def process_notification_creation(update, context, user_id, user_db_id):
    """Обрабатывает шаги создания напоминания"""
    try:
        state = notification_states[user_id]['state']
        text = update.message.text
        
        # Обработка в зависимости от текущего состояния
        if state == NOTIFICATION_TEXT:
            # Сохраняем текст напоминания
            notification_states[user_id]['text'] = text
            notification_states[user_id]['state'] = NOTIFICATION_DATE
            
            # Запрашиваем дату
            await write_translated_message("Введите дату напоминания в формате ДД.ММ.ГГГГ (например, 31.12.2023):")
            
        elif state == NOTIFICATION_DATE:
            # Проверяем формат даты
            try:
                date = datetime.strptime(text, "%d.%m.%Y").date()
                today = datetime.now().date()
                
                # Проверяем, что дата не в прошлом
                if date < today:
                    await write_translated_message("Дата не может быть в прошлом. Пожалуйста, введите будущую дату:")
                    return
                    
                # Сохраняем дату
                notification_states[user_id]['date'] = date
                notification_states[user_id]['state'] = NOTIFICATION_TIME
                
                # Запрашиваем время
                await write_translated_message("Введите время напоминания в формате ЧЧ:ММ (например, 14:30):")
                
            except ValueError:
                await write_translated_message("Неверный формат даты. Пожалуйста, используйте формат ДД.ММ.ГГГГ (например, 31.12.2023):")
                
        elif state == NOTIFICATION_TIME:
            # Проверяем формат времени
            try:
                time = datetime.strptime(text, "%H:%M").time()
                
                # Если дата сегодня, проверяем что время не в прошлом
                date = notification_states[user_id]['date']
                now = datetime.now()
                
                if date == now.date() and time < now.time():
                    await write_translated_message("Время не может быть в прошлом. Пожалуйста, введите будущее время:")
                    return
                    
                # Сохраняем время
                notification_states[user_id]['time'] = time
                
                # Создаем напоминание
                notification_text = notification_states[user_id]['text']
                notification_date = notification_states[user_id]['date']
                notification_time = notification_states[user_id]['time']
                
                # Добавляем напоминание в БД
                result = await add_notification_to_db(
                    user_db_id, 
                    notification_text, 
                    notification_time, 
                    notification_date
                )
                
                if result:
                    # Форматируем дату и время для ответа
                    date_str = notification_date.strftime('%d.%m.%Y')
                    time_str = notification_time.strftime('%H:%M')
                    
                    success_message = f"Напоминание успешно создано!\n\n"
                    success_message += f"📝 Текст: {notification_text}\n"
                    success_message += f"📅 Дата: {date_str}\n"
                    success_message += f"⏰ Время: {time_str}"
                    
                    # Добавляем кнопку "В главное меню"
                    reply_markup = InlineKeyboardMarkup([[
                        InlineKeyboardButton("В главное меню", callback_data="back_to_main")
                    ]])
                    
                    # Переводим сообщение
                    translated_text = await translate(success_message)
                    await update.message.reply_text(
                        text=translated_text,
                        reply_markup=reply_markup
                    )
                else:
                    # Показываем сообщение об ошибке
                    await show_error_with_menu_button("Не удалось создать напоминание. Пожалуйста, попробуйте позже.")
                
                # Удаляем состояние создания напоминания
                del notification_states[user_id]
                
            except ValueError:
                await write_translated_message("Неверный формат времени. Пожалуйста, используйте формат ЧЧ:ММ (например, 14:30):")
    except Exception as e:
        print(f"Ошибка при обработке создания напоминания: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            # Показываем сообщение об ошибке
            await show_error_with_menu_button("Произошла ошибка при создании напоминания. Пожалуйста, попробуйте позже.")
            
            # Очищаем состояние, если произошла ошибка
            if user_id in notification_states:
                del notification_states[user_id]
                
        except Exception as msg_error:
            print(f"Ошибка при отправке сообщения об ошибке: {msg_error}")

# Добавление напоминания в БД
async def add_notification_to_db(user_db_id, notification_text, notification_time, notification_date):
    """Добавляет напоминание в базу данных"""
    if not db_initialized:
        print("PostgreSQL не инициализирован")
        return False
    
    max_retries = 3
    for attempt in range(max_retries):
        connection = None
        try:
            async with db_lock:
                # Создаем новое соединение
                connection = await get_db_connection()
                if connection is None:
                    if attempt < max_retries - 1:
                        print("Не удалось создать соединение, пробуем снова...")
                        await asyncio.sleep(1)
                        continue
                    else:
                        print("Не удалось создать соединение после всех попыток")
                        return False
                
                # Добавляем напоминание
                notification_id = await connection.fetchval(
                    f'''
                    INSERT INTO {BOT_PREFIX}notifications 
                    (user_id, notification_text, notification_time, notification_date)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                    ''',
                    user_db_id, notification_text, notification_time, notification_date
                )
                
                print(f"Добавлено новое напоминание для пользователя {user_db_id}")
                return notification_id
                
        except Exception as e:
            print(f"Ошибка при добавлении напоминания (попытка {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print("Повторная попытка через 1 секунду...")
                await asyncio.sleep(1)
            else:
                return False
        finally:
            # Закрываем соединение в любом случае
            if connection:
                await connection.close()
    
    return False

# Получение списка напоминаний пользователя
async def get_user_notifications(user_db_id, show_sent=False, show_deleted=False):
    """Получает список напоминаний пользователя из базы данных"""
    if not db_initialized:
        print("PostgreSQL не инициализирован")
        return []
    
    max_retries = 3
    for attempt in range(max_retries):
        connection = None
        try:
            async with db_lock:
                # Создаем новое соединение
                connection = await get_db_connection()
                if connection is None:
                    if attempt < max_retries - 1:
                        print("Не удалось создать соединение, пробуем снова...")
                        await asyncio.sleep(1)
                        continue
                    else:
                        print("Не удалось создать соединение после всех попыток")
                        return []
                
                # Создаем условия для фильтрации
                conditions = ["user_id = $1"]
                params = [user_db_id]
                
                if not show_sent:
                    conditions.append("is_sent = FALSE")
                
                if not show_deleted:
                    conditions.append("is_deleted = FALSE")
                
                # Формируем запрос
                query = f'''
                SELECT id, notification_text, notification_time, notification_date, created_at, is_sent
                FROM {BOT_PREFIX}notifications
                WHERE {" AND ".join(conditions)}
                ORDER BY notification_date ASC, notification_time ASC
                '''
                
                # Получаем напоминания
                results = await connection.fetch(query, *params)
                
                # Преобразуем результаты в список словарей
                notifications = []
                for row in results:
                    notifications.append({
                        'id': row['id'],
                        'text': row['notification_text'],
                        'time': row['notification_time'],
                        'date': row['notification_date'],
                        'created_at': row['created_at'],
                        'is_sent': row['is_sent']
                    })
                
                return notifications
                
        except Exception as e:
            print(f"Ошибка при получении напоминаний (попытка {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print("Повторная попытка через 1 секунду...")
                await asyncio.sleep(1)
            else:
                return []
        finally:
            # Закрываем соединение в любом случае
            if connection:
                await connection.close()
    
    return []

# Получение активных напоминаний для отправки
async def get_active_notifications(current_date, current_time):
    """Получает список активных напоминаний, которые нужно отправить"""
    if not db_initialized:
        print("PostgreSQL не инициализирован")
        return []
    
    max_retries = 3
    for attempt in range(max_retries):
        connection = None
        try:
            async with db_lock:
                # Создаем новое соединение
                connection = await get_db_connection()
                if connection is None:
                    if attempt < max_retries - 1:
                        print("Не удалось создать соединение, пробуем снова...")
                        await asyncio.sleep(1)
                        continue
                    else:
                        print("Не удалось создать соединение после всех попыток")
                        return []
                
                # Формируем запрос для получения напоминаний, которые нужно отправить
                query = f'''
                SELECT n.id, n.notification_text, n.notification_time, n.notification_date, u.user_id, u.chat_id
                FROM {BOT_PREFIX}notifications n
                JOIN {BOT_PREFIX}users u ON n.user_id = u.id
                WHERE n.notification_date = $1 
                AND n.notification_time <= $2
                AND n.is_sent = FALSE
                AND n.is_deleted = FALSE
                '''
                
                # Получаем напоминания
                results = await connection.fetch(query, current_date, current_time)
                
                # Преобразуем результаты в список словарей
                notifications = []
                for row in results:
                    notifications.append({
                        'id': row['id'],
                        'text': row['notification_text'],
                        'time': row['notification_time'],
                        'date': row['notification_date'],
                        'user_id': row['user_id'],
                        'chat_id': row['chat_id']
                    })
                
                return notifications
                
        except Exception as e:
            print(f"Ошибка при получении активных напоминаний (попытка {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print("Повторная попытка через 1 секунду...")
                await asyncio.sleep(1)
            else:
                return []
        finally:
            # Закрываем соединение в любом случае
            if connection:
                await connection.close()
    
    return []

# Пометить напоминание как отправленное
async def mark_notification_as_sent(notification_id):
    """Помечает напоминание как отправленное"""
    if not db_initialized:
        print("PostgreSQL не инициализирован")
        return False
    
    max_retries = 3
    for attempt in range(max_retries):
        connection = None
        try:
            async with db_lock:
                # Создаем новое соединение
                connection = await get_db_connection()
                if connection is None:
                    if attempt < max_retries - 1:
                        print("Не удалось создать соединение, пробуем снова...")
                        await asyncio.sleep(1)
                        continue
                    else:
                        print("Не удалось создать соединение после всех попыток")
                        return False
                
                # Обновляем статус напоминания
                await connection.execute(
                    f'''
                    UPDATE {BOT_PREFIX}notifications
                    SET is_sent = TRUE
                    WHERE id = $1
                    ''',
                    notification_id
                )
                
                return True
                
        except Exception as e:
            print(f"Ошибка при обновлении статуса напоминания (попытка {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print("Повторная попытка через 1 секунду...")
                await asyncio.sleep(1)
            else:
                return False
        finally:
            # Закрываем соединение в любом случае
            if connection:
                await connection.close()
    
    return False

# Удалить напоминание
async def delete_notification(notification_id):
    """Помечает напоминание как удаленное"""
    if not db_initialized:
        print("PostgreSQL не инициализирован")
        return False
    
    max_retries = 3
    for attempt in range(max_retries):
        connection = None
        try:
            async with db_lock:
                # Создаем новое соединение
                connection = await get_db_connection()
                if connection is None:
                    if attempt < max_retries - 1:
                        print("Не удалось создать соединение, пробуем снова...")
                        await asyncio.sleep(1)
                        continue
                    else:
                        print("Не удалось создать соединение после всех попыток")
                        return False
                
                # Обновляем статус напоминания
                await connection.execute(
                    f'''
                    UPDATE {BOT_PREFIX}notifications
                    SET is_deleted = TRUE
                    WHERE id = $1
                    ''',
                    notification_id
                )
                
                return True
                
        except Exception as e:
            print(f"Ошибка при удалении напоминания (попытка {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                print("Повторная попытка через 1 секунду...")
                await asyncio.sleep(1)
            else:
                return False
        finally:
            # Закрываем соединение в любом случае
            if connection:
                await connection.close()
    
    return False

# Функция для запуска бота
def run_bot(token=None):
    """Запускает бота с заданным токеном"""
    global BOT_TOKEN
    
    # Если токен передан явно
    if token:
        BOT_TOKEN = token
    # Иначе пытаемся загрузить из конфигурации
    elif not BOT_TOKEN:
        if not load_token():
            print("ОШИБКА: Токен бота не задан!")
            print("Опции:")
            print("1. Вставьте токен в файл credentials/telegram/token.txt")
            print("2. Создайте модуль credentials/telegram/config.py с переменной BOT_TOKEN")
            print("3. Передайте токен явно в функцию run_bot()")
            return
    
    # Настройка логирования
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("reload_bot", reload_bot_command))  # Перезапуск бота
    application.add_handler(CommandHandler("create_notification", create_notification_command))  # Создание напоминания
    application.add_handler(CommandHandler("list_notifications", list_notifications_command))  # Список напоминаний
    application.add_handler(CommandHandler("delete_notification", delete_notification_command))  # Удаление напоминания
    application.add_handler(CommandHandler("check_notifications", check_notifications_command))  # Ручная проверка напоминаний
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    # Добавление обработчика ошибок
    application.add_error_handler(error_handler)
    
    # Создаем функцию для периодической проверки напоминаний
    async def check_notifications_task(context):
        await check_and_send_notifications(context.bot)
    
    # Проверяем, доступен ли job_queue
    if hasattr(application, 'job_queue') and application.job_queue is not None:
        try:
            # Добавляем задачу в планировщик
            application.job_queue.run_repeating(
                check_notifications_task,
                interval=60,  # проверяем каждую минуту
                first=10  # первый запуск через 10 секунд после старта
            )
            print("Планировщик задач для напоминаний настроен")
        except Exception as e:
            print(f"Ошибка при настройке планировщика: {e}")
            print("Автоматическая проверка напоминаний не будет работать!")
    else:
        print("ВНИМАНИЕ: job_queue не доступен. Установите python-telegram-bot[job-queue]")
        print("Автоматическая проверка напоминаний не будет работать!")
    
    # Запуск бота - НЕ используем await, так как этот метод сам запускает свой цикл событий
    print(f"Бот запущен! Нажмите Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

# Пример использования
if __name__ == "__main__":
    # Инициализируем базу данных перед запуском бота
    async def init_db():
        db_initialized = await setup_db()
        print(f"База данных инициализирована: {db_initialized}")
        return db_initialized
    
    try:
        # Запускаем инициализацию БД в отдельном цикле событий
        db_successful = asyncio.run(init_db())
        
        # Проверяем, успешно ли инициализирована БД
        if not db_successful:
            print("ОШИБКА: Не удалось подключиться к базе данных!")
            print("Бот не может работать без подключения к PostgreSQL.")
            print("Проверьте настройки в credentials/postgres/config.py")
            exit(1)  # Выходим с кодом ошибки
        
        # Создаем новый цикл событий перед запуском бота
        asyncio.set_event_loop(asyncio.new_event_loop())
        
        # Запускаем бота (не в асинхронном контексте)
        run_bot()
    except KeyboardInterrupt:
        print("Бот остановлен пользователем")
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
        import traceback
        traceback.print_exc()

# Функция для показа сообщения "нет" с кнопкой возврата в меню
async def show_not_found_with_menu_button(update=None, context=None):
    """Показывает сообщение "(нет)" с кнопкой возврата в меню"""
    try:
        # Определяем, откуда пришел запрос - из глобальных переменных или из параметров
        update_obj = update or current_update
        
        if not update_obj:
            print("Ошибка: update не доступен")
            return
            
        # Создаем кнопку возврата в меню
        reply_markup = InlineKeyboardMarkup([[
            InlineKeyboardButton("Вернуться в главное меню", callback_data="back_to_main")
        ]])
        
        # Отправляем сообщение
        if update_obj.callback_query:
            await update_obj.callback_query.edit_message_text(
                text="(нет)",
                reply_markup=reply_markup
            )
        elif hasattr(update_obj, 'message') and update_obj.message:
            await update_obj.message.reply_text(
                text="(нет)",
                reply_markup=reply_markup
            )
    except Exception as e:
        print(f"Ошибка при показе сообщения '(нет)': {e}")
        import traceback
        traceback.print_exc()

# Функция для обновления текущего контекста
def update_context(update, context):
    """Обновляет глобальные переменные current_update и current_context"""
    global current_update, current_context
    
    print(f"Обновление контекста: update={update is not None}, context={context is not None}")
    
    current_update = update
    current_context = context
    return update, context 