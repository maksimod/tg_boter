import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Настройки бота
BOT_TOKEN = "7557691355:AAFomvlkd0tU-r3IFn23KQjcv4k3qKwRk3o"  # Вставьте сюда ваш токен
TIMEOUT = 30

# Глобальные переменные
callbacks = {}
current_update = None
current_context = None

# Функция для отправки сообщения
async def write_message(text):
    """Простая функция для отправки сообщения"""
    if current_update and current_context:
        if current_update.callback_query:
            await current_update.callback_query.edit_message_text(text=text)
        else:
            await current_update.message.reply_text(text=text)

# Функция для создания кнопок
async def button(buttons_layout):
    """Создает кнопки из простого списка
    
    Пример использования:
    button([
        ["Кнопка 1", "callback_1"],
        ["Кнопка 2", "callback_2"],
        [["Кнопка 3", "callback_3"], ["Кнопка 4", "callback_4"]]
    ])
    """
    keyboard = []
    
    for row in buttons_layout:
        if isinstance(row[0], list):
            # Это строка с несколькими кнопками
            keyboard_row = []
            for btn in row:
                keyboard_row.append(InlineKeyboardButton(btn[0], callback_data=btn[1]))
            keyboard.append(keyboard_row)
        else:
            # Это одна кнопка в строке
            keyboard.append([InlineKeyboardButton(row[0], callback_data=row[1])])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if current_update and current_context:
        if current_update.callback_query:
            await current_update.callback_query.edit_message_reply_markup(reply_markup=reply_markup)
        else:
            await current_update.message.reply_text(
                text="Выберите опцию:",
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
                keyboard_row.append(InlineKeyboardButton(btn[0], callback_data=btn[1]))
            keyboard.append(keyboard_row)
        else:
            # Это одна кнопка в строке
            keyboard.append([InlineKeyboardButton(row[0], callback_data=row[1])])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if current_update and current_context:
        if current_update.callback_query:
            await current_update.callback_query.edit_message_text(
                text=text,
                reply_markup=reply_markup
            )
        else:
            await current_update.message.reply_text(
                text=text,
                reply_markup=reply_markup
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
    
    # Запускаем пользовательскую функцию
    if 'start' in callbacks:
        await callbacks['start']()
    else:
        await write_message("Привет! Я бот. Используйте /help для помощи.")

# Обработчик callback запросов
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_update, current_context
    current_update = update
    current_context = context
    
    callback_data = update.callback_query.data
    
    # Запускаем соответствующий обработчик
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
    
    if token:
        BOT_TOKEN = token
    
    if not BOT_TOKEN:
        print("ОШИБКА: Токен бота не задан!")
        print("Вставьте токен в файл easy_bot.py или передайте его в функцию run_bot()")
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

# Пример использования:
if __name__ == "__main__":
    # Вставьте сюда ваш токен
    BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
    
    @on_start
    async def handle_start():
        await write_message("Привет! Выберите цвет:")
        await button([
            ["Зеленый", "callback_green"],
            ["Красный", "callback_red"],
            [["Белый", "callback_white"], ["Черный", "callback_black"]]
        ])
    
    @on_callback("callback_green")
    async def handle_green():
        await write_message("Вы выбрали зеленый цвет!")
        
    @on_callback("callback_red")
    async def handle_red():
        await write_message("Вы выбрали красный цвет!")
        
    @on_callback("callback_white")
    async def handle_white():
        await write_message("Вы выбрали белый цвет!")
        
    @on_callback("callback_black")
    async def handle_black():
        await write_message("Вы выбрали черный цвет!")
    
    # Запускаем бота
    run_bot() 