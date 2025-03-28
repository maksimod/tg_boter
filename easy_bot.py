import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Импортируем функцию перевода
try:
    from language.translate_any_message import translate_any_message
    print("Translation module imported successfully")
except ImportError as e:
    print(f"Error importing translation module: {e}")
    translate_any_message = None

# Настройки бота
BOT_TOKEN = ""  # Будет загружен из файла конфигурации
TIMEOUT = 30

# Глобальные переменные
callbacks = {}
current_update = None
current_context = None

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
    
    try:
        # Используем функцию перевода из старого бота
        translated_text = await translate_any_message(
            text,
            target_language,
            source_language="Russian",
            on_translate_start=None,
            on_translate_end=None
        )
        return translated_text
    except Exception as e:
        logging.error(f"Ошибка при переводе: {e}")
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
    
    # Если у пользователя нет выбранного языка, показываем выбор языка
    if 'language' not in context.user_data:
        await show_language_selection()
        return
    
    # Запускаем пользовательскую функцию
    if 'start' in callbacks:
        await callbacks['start']()
    else:
        await write_translated_message("Привет! Я бот. Используйте /help для помощи.")

# Обработчик callback запросов
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_update, current_context
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
        await callbacks[callback_data]()
    else:
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
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Запуск бота
    print(f"Бот запущен! Нажмите Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

# Пример использования
if __name__ == "__main__":
    @on_start
    async def handle_start():
        await write_translated_message("Привет! Выберите цвет:")
        await button([
            ["Зеленый", "callback_green"],
            ["Красный", "callback_red"],
            [["Белый", "callback_white"], ["Черный", "callback_black"]]
        ])
    
    @on_callback("callback_green")
    async def handle_green():
        await write_translated_message("Вы выбрали зеленый цвет!")
    
    run_bot() 