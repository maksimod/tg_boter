import logging
import os
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Экспорт функций
__all__ = [
    'write_translated_message', 'button', 'message_with_buttons', 
    'start', 'callback', 'run_bot', 'get_callback', 'get_user_language',
    'on_text_message', 'translate',
    # Новые авто-функции
    'auto_write_translated_message', 'auto_button', 'auto_message_with_buttons',
    'start', 'callback', 'on_auto_text_message', 'auto_translate'
]

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
chatgpt_handler = None  # Обработчик для ChatGPT запросов

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

# Импортируем обработчик опросов, если доступен
try:
    from base.survey import handle_survey_response
    print("Survey module imported successfully")
    has_survey_module = True
except ImportError as e:
    print(f"Error importing survey module: {e}")
    has_survey_module = False

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
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    global current_update, current_context
    current_update = update
    current_context = context
    
    # Получаем id пользователя в БД
    user_db_id = context.user_data.get('db_user_id')
    
    # Если пользователь еще не в БД, добавляем его
    if not user_db_id and update.effective_user:
        user = update.effective_user
        chat_id = update.effective_chat.id
        user_db_id = await add_user_to_db(user.id, chat_id, user.username)
        context.user_data['db_user_id'] = user_db_id
    
    # Сохраняем сообщение в БД
    if user_db_id and update.message and update.message.text:
        await add_message_to_db(user_db_id, update.message.text)
    
    # Если у пользователя нет выбранного языка, показываем выбор языка
    if 'language' not in context.user_data:
        await show_language_selection()
        return
    
    # Проверяем, есть ли обработчик опросов и активный опрос
    if has_survey_module:
        try:
            survey_handled = await handle_survey_response(update, context)
            if survey_handled:
                return
        except Exception as e:
            logging.error(f"Ошибка при обработке опроса: {e}")
    
    # Проверяем, есть ли обработчик для ChatGPT
    if chatgpt_handler and update.message and update.message.text:
        try:
            await chatgpt_handler(update.message.text)
            return
        except Exception as e:
            logging.error(f"Ошибка при обработке ChatGPT запроса: {e}")
    
    # Если есть обработчик для текстовых сообщений, вызываем его
    if 'text_message' in callbacks and update.message and update.message.text:
        await callbacks['text_message'](update.message.text)
    else:
        # По умолчанию просто отвечаем эхом
        if update.message and update.message.text:
            await write_translated_message(f"Вы написали: {update.message.text}")

# Обработчик callback запросов
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_update, current_context
    current_update = update
    current_context = context
    
    callback_data = update.callback_query.data
    print(f"[HANDLER] Received callback query: {callback_data}")
    
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
    
    # Проверяем, есть ли обработчик опросов и пробуем обработать выбор кнопки
    if has_survey_module:
        try:
            survey_handled = await handle_survey_response(update, context)
            if survey_handled:
                return
        except Exception as e:
            logging.error(f"Ошибка при обработке callback опроса: {e}")
            import traceback
            traceback.print_exc()
    
    # Запускаем соответствующий обработчик callback
    if callback_data in callbacks:
        try:
            callback_func = callbacks[callback_data]
            print(f"[HANDLER] Calling callback function for {callback_data}")
            # Действительно асинхронно вызываем callback функцию
            await callback_func()
            print(f"[HANDLER] Callback function for {callback_data} completed")
        except Exception as e:
            logging.error(f"Ошибка при выполнении callback {callback_data}: {e}")
            import traceback
            traceback.print_exc()
            await update.callback_query.answer(text=f"Ошибка при обработке: {e}")
    else:
        await update.callback_query.answer(text=f"Обработчик для {callback_data} не найден")

# Функция для регистрации обработчика команды /start
def on_start(func):
    """Регистрирует функцию как обработчик команды /start"""
    callbacks['start'] = func
    return func

# Функция для регистрации обработчика callback
def callback(callback_data):
    """
    Декоратор для регистрации функции как обработчика callback
    с автоматическим запуском асинхронных функций
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            print(f"[CALLBACK] Executing callback {callback_data} with args: {args}")
            try:
                result = func(*args, **kwargs)
                print(f"[CALLBACK] Function {callback_data} returned: {result}")
                
                # Запускаем автоматические функции
                if current_context and 'auto_functions' in current_context.user_data:
                    for f in current_context.user_data['auto_functions']:
                        await f()
                    current_context.user_data['auto_functions'] = []
                
                return result
            except Exception as e:
                print(f"[CALLBACK] Error in callback {callback_data}: {e}")
                import traceback
                traceback.print_exc()
                raise

        callbacks[callback_data] = async_wrapper
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
    application.add_handler(CommandHandler("reload_bot", reload_bot_command))  # Новый обработчик
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    # Добавление обработчика ошибок
    application.add_error_handler(error_handler)
    
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

# Добавляем новые функции-обертки для упрощения использования бота
def auto_write_translated_message(text):
    """
    Синхронная обертка для write_translated_message.
    Автоматически запускает асинхронную функцию в текущем обработчике.
    """
    async def wrapper():
        await write_translated_message(text)
    
    if 'auto_functions' not in current_context.user_data:
        current_context.user_data['auto_functions'] = []
    
    current_context.user_data['auto_functions'].append(wrapper)
    return wrapper

def auto_button(buttons_layout):
    """
    Синхронная обертка для button.
    Автоматически запускает асинхронную функцию в текущем обработчике.
    """
    async def wrapper():
        await button(buttons_layout)
    
    if 'auto_functions' not in current_context.user_data:
        current_context.user_data['auto_functions'] = []
    
    current_context.user_data['auto_functions'].append(wrapper)
    return wrapper

def auto_message_with_buttons(text, buttons_layout):
    """
    Синхронная обертка для message_with_buttons.
    Автоматически запускает асинхронную функцию в текущем обработчике.
    """
    async def wrapper():
        await message_with_buttons(text, buttons_layout)
    
    if 'auto_functions' not in current_context.user_data:
        current_context.user_data['auto_functions'] = []
    
    current_context.user_data['auto_functions'].append(wrapper)
    return wrapper

def auto_translate(text, target_lang=None):
    """
    Синхронная обертка для translate.
    Автоматически запускает асинхронную функцию и возвращает результат.
    """
    async def wrapper():
        return await translate(text, target_lang)
    
    if 'auto_functions' not in current_context.user_data:
        current_context.user_data['auto_functions'] = []
    
    current_context.user_data['auto_functions'].append(wrapper)
    return wrapper

# Модифицируем декораторы для автоматического запуска асинхронных функций
def start(func):
    """
    Регистрирует функцию как обработчик команды /start
    с автоматическим запуском асинхронных функций
    """
    async def wrapper():
        func()
        if current_context and 'auto_functions' in current_context.user_data:
            for f in current_context.user_data['auto_functions']:
                await f()
            current_context.user_data['auto_functions'] = []

    callbacks['start'] = wrapper
    return func

def on_auto_text_message(func):
    """
    Регистрирует функцию как обработчик текстовых сообщений
    с автоматическим запуском асинхронных функций
    """
    async def wrapper(text):
        func(text)
        if current_context and 'auto_functions' in current_context.user_data:
            for f in current_context.user_data['auto_functions']:
                await f()
            current_context.user_data['auto_functions'] = []

    callbacks['text_message'] = wrapper
    return func

# Регистрация обработчика ChatGPT
def register_chatgpt_handler(handler):
    """Регистрирует обработчик для сообщений ChatGPT"""
    global chatgpt_handler
    chatgpt_handler = handler 