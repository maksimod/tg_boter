import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, Application, MessageHandler, filters

from easy_bot import (
    # Импортируем основные функции
    setup_db, run_bot, translate, load_token,
    
    # Импортируем функции для работы с напоминаниями
    create_notification_command, list_notifications_command, delete_notification_command,
    check_notifications_command, 
    
    # Импортируем функцию для отображения "(нет)"
    show_not_found_with_menu_button,
    
    # Импортируем обработчик для перезапуска бота
    reload_bot_command
)

# Глобальная переменная для хранения токена бота
BOT_TOKEN = None

# Обработчик команды /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await show_main_menu(update, context)

# Показать главное меню
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает главное меню бота"""
    keyboard = [
        [
            InlineKeyboardButton("🔍 Поиск информации", callback_data="search_info"),
            InlineKeyboardButton("📅 Создать напоминание", callback_data="create_reminder")
        ],
        [
            InlineKeyboardButton("📋 Мои напоминания", callback_data="list_reminders"),
            InlineKeyboardButton("🔔 Проверить напоминания", callback_data="check_reminders")
        ],
        [
            InlineKeyboardButton("ℹ️ О боте", callback_data="about_bot")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Проверяем, это новое сообщение или обновление существующего
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text="Добро пожаловать в бота! Выберите действие:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            text="Добро пожаловать в бота! Выберите действие:",
            reply_markup=reply_markup
        )

# Обработчик callback запросов
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатия на кнопки"""
    query = update.callback_query
    await query.answer()  # Отвечаем на callback запрос
    
    callback_data = query.data
    print(f"Обработка callback: {callback_data}")
    
    # Обработка выбора языка
    if callback_data.startswith("lang_"):
        language = callback_data.replace("lang_", "")
        if hasattr(context, "user_data"):
            context.user_data["language"] = language
        await show_main_menu(update, context)
    
    elif callback_data == "search_info":
        # Поиск информации
        keyboard = [[InlineKeyboardButton("◀️ Вернуться в главное меню", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="Функция поиска информации в разработке...",
            reply_markup=reply_markup
        )
    
    elif callback_data == "create_reminder":
        # Создание напоминания
        await create_notification_command(update, context)
    
    elif callback_data == "list_reminders":
        # Список напоминаний
        await list_notifications_command(update, context)
    
    elif callback_data == "check_reminders":
        # Проверка напоминаний
        await check_notifications_command(update, context)
    
    elif callback_data == "about_bot":
        # О боте
        about_text = (
            "Это многофункциональный бот с возможностью создания напоминаний. "
            "Вы можете создавать напоминания, и бот уведомит вас в указанное время.\n\n"
            "Доступные команды:\n"
            "/start - начать работу с ботом\n"
            "/reload_bot - перезапустить бота\n"
            "/create_notification - создать новое напоминание\n"
            "/list_notifications - показать список напоминаний\n"
            "/delete_notification [номер] - удалить напоминание\n"
            "/check_notifications - проверить и отправить напоминания вручную"
        )
        
        keyboard = [[InlineKeyboardButton("◀️ Вернуться в главное меню", callback_data="back_to_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=about_text,
            reply_markup=reply_markup
        )
    
    elif callback_data == "back_to_main":
        # Возврат в главное меню
        await show_main_menu(update, context)

# Обработчик текстовых сообщений
async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения"""
    # Просто отвечаем главным меню
    await show_main_menu(update, context)

# Загружаем токен бота напрямую
def load_bot_token():
    """Загружает токен бота напрямую из файла конфигурации"""
    try:
        import os
        
        # Путь к файлу конфигурации
        config_path = os.path.join(os.path.dirname(__file__), 'credentials', 'telegram', 'config.py')
        
        # Проверяем, существует ли файл
        if os.path.exists(config_path):
            # Читаем файл как текст и извлекаем токен
            with open(config_path, 'r', encoding='utf-8') as file:
                content = file.read()
                # Ищем строку с BOT_TOKEN
                for line in content.split('\n'):
                    if line.startswith('BOT_TOKEN'):
                        # Извлекаем значение токена
                        token = line.split('=')[1].strip().strip('"\'')
                        print("Токен загружен из credentials/telegram/config.py")
                        return token
        
        # Пробуем загрузить токен из token.txt
        token_path = os.path.join(os.path.dirname(__file__), 'credentials', 'telegram', 'token.txt')
        if os.path.exists(token_path):
            with open(token_path, 'r') as file:
                token = file.read().strip()
                if token:
                    print("Токен загружен из credentials/telegram/token.txt")
                    return token
        
        print("Токен не найден")
        return None
    except Exception as e:
        print(f"Ошибка при загрузке токена: {e}")
        return None

# Основная точка входа
if __name__ == "__main__":
    try:
        # Загружаем токен напрямую
        BOT_TOKEN = load_bot_token()
        if not BOT_TOKEN:
            print("ОШИБКА: Токен бота не загружен!")
            exit(1)
        
        print(f"Токен бота успешно загружен")
        
        # Используем синхронный код для инициализации, чтобы избежать проблем с циклом событий
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Инициализируем базу данных
        db_initialized = loop.run_until_complete(setup_db())
        print(f"База данных инициализирована: {db_initialized}")
        
        if not db_initialized:
            print("ОШИБКА: Не удалось подключиться к базе данных!")
            print("Бот не может работать без подключения к PostgreSQL.")
            print("Проверьте настройки в credentials/postgres/config.py")
            exit(1)
        
        # Создаем приложение
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("reload_bot", reload_bot_command))
        application.add_handler(CommandHandler("create_notification", create_notification_command))
        application.add_handler(CommandHandler("list_notifications", list_notifications_command))
        application.add_handler(CommandHandler("delete_notification", delete_notification_command))
        application.add_handler(CommandHandler("check_notifications", check_notifications_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))
        
        # Запускаем бота
        print("Бот запущен! Нажмите Ctrl+C для остановки.")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем")
    except Exception as e:
        print(f"\nОшибка при запуске бота: {e}")
        import traceback
        traceback.print_exc() 