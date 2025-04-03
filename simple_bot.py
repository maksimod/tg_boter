#!/usr/bin/env python3
"""
Простой интерфейс для работы с системой уведомлений Telegram бота.
Позволяет легко интегрировать функцию создания уведомлений в другие приложения.

Основные функции:
- create_reminder - создать новое напоминание
- get_reminders - получить список активных напоминаний пользователя
- init_bot - инициализировать и запустить бота

Пример использования:
    from simple_bot import create_reminder, init_bot
    from datetime import datetime, timedelta
    import pytz
    
    # Инициализация бота при запуске приложения
    bot = init_bot()
    
    # Создание уведомления для пользователя 
    moscow_tz = pytz.timezone('Europe/Moscow')
    notification_time = moscow_tz.localize(datetime.now() + timedelta(minutes=5))
    create_reminder(user_id=123456789, notification_text="Не забудь позвонить маме!", notification_time=notification_time)
"""

import os
import pytz
import logging
import time
from datetime import datetime
from threading import Thread
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import asyncio

# Загружаем переменные окружения из .env файла
load_dotenv()

# Импортируем конфигурации
from credentials.telegram.config import BOT_TOKEN

# Константы для состояний разговора
WAITING_FOR_DATE = 0
WAITING_FOR_MESSAGE = 1

# Импортируем функции для работы с базой данных и уведомлениями
from database import (
    MOSCOW_TZ, init_database, save_user, save_message, create_notification, 
    get_user_notifications, get_db_time, get_all_user_notifications
)
from notifications import check_notifications, scheduled_job, fix_timezones

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='simple_bot.log'
)
logger = logging.getLogger(__name__)

# Глобальный объект для доступа к боту
_bot_app = None

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Сохраняем пользователя в БД
    save_user(user.id, user.first_name, user.username)
    
    await update.message.reply_text(
        f"Привет, {user.first_name}! Я бот для создания уведомлений.\n\n"
        "Чтобы создать новое уведомление, используйте команду /notify.\n"
        "Чтобы посмотреть все активные уведомления, используйте команду /list."
    )

# Обработчик команды /notify
async def notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Сохраняем сообщение в БД
    save_message(update.effective_user.id, update.message.text)
    
    await update.message.reply_text(
        "Пожалуйста, введите дату и время уведомления в формате ДД.ММ.ГГ ЧЧ:ММ\n"
        "Например: 03.04.25 16:45"
    )
    return WAITING_FOR_DATE

# Обработчик ввода даты и времени
async def get_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Сохраняем сообщение в БД
    save_message(update.effective_user.id, update.message.text)
    
    date_str = update.message.text.strip()
    try:
        # Парсим дату и время из ввода пользователя
        notification_time = datetime.strptime(date_str, "%d.%m.%y %H:%M")
        # Добавляем информацию о часовом поясе
        notification_time = MOSCOW_TZ.localize(notification_time)
        
        # Проверяем, что дата не в прошлом
        now = datetime.now(MOSCOW_TZ)
        if notification_time <= now:
            await update.message.reply_text("Указанная дата и время уже прошли. Пожалуйста, введите будущую дату и время.")
            return WAITING_FOR_DATE
        
        # Сохраняем дату в контексте
        context.user_data['notification_time'] = notification_time
        
        await update.message.reply_text(
            f"Уведомление будет отправлено {notification_time.strftime('%d.%m.%Y в %H:%M')} (МСК).\n"
            f"Теперь введите текст уведомления:"
        )
        return WAITING_FOR_MESSAGE
    except ValueError:
        await update.message.reply_text(
            "Неверный формат даты. Пожалуйста, используйте формат ДД.ММ.ГГ ЧЧ:ММ\n"
            "Например: 03.04.25 16:45"
        )
        return WAITING_FOR_DATE

# Обработчик ввода текста уведомления
async def get_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Сохраняем сообщение в БД
    save_message(update.effective_user.id, update.message.text)
    
    message_text = update.message.text.strip()
    notification_time = context.user_data['notification_time']
    
    # Логируем параметры уведомления
    logger.info(f"Создание уведомления для пользователя {update.effective_user.id} на {notification_time.strftime('%d.%m.%Y %H:%M')} с текстом: {message_text}")
    
    # Создаем уведомление в БД
    create_notification(update.effective_user.id, message_text, notification_time)
    
    # Текущее московское время для сравнения
    now = datetime.now(MOSCOW_TZ)
    time_diff = notification_time - now
    hours, remainder = divmod(time_diff.total_seconds(), 3600)
    minutes, _ = divmod(remainder, 60)
    time_str = f"{int(hours)} ч {int(minutes)} мин"
    
    await update.message.reply_text(
        f"Уведомление создано! {notification_time.strftime('%d.%m.%Y в %H:%M')} (МСК) "
        f"вы получите сообщение: \"{message_text}\"\n\n"
        f"До уведомления осталось: {time_str}"
    )
    
    # Очищаем данные пользователя
    context.user_data.clear()
    
    return ConversationHandler.END

# Обработчик команды /list
async def list_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Сохраняем сообщение в БД
    save_message(update.effective_user.id, update.message.text)
    
    # Получаем уведомления пользователя
    user_notifications = get_user_notifications(update.effective_user.id)
    
    if not user_notifications:
        await update.message.reply_text("У вас нет активных уведомлений.")
        return
    
    # Форматируем список уведомлений
    notifications_text = "Ваши активные уведомления:\n\n"
    for i, (notification_id, notification_text, notification_time) in enumerate(user_notifications, 1):
        notifications_text += f"{i}. {notification_time.strftime('%d.%m.%Y %H:%M')} - {notification_text}\n"
    
    await update.message.reply_text(notifications_text)

# Обработчик команды /cancel для отмены создания уведомления
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Сохраняем сообщение в БД
    save_message(update.effective_user.id, update.message.text)
    
    context.user_data.clear()
    await update.message.reply_text("Создание уведомления отменено.")
    return ConversationHandler.END

# Обработчик команды /debug - показывает информацию о базе данных
async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Сохраняем сообщение в БД
    save_message(update.effective_user.id, update.message.text)
    
    # Получаем текущее время сервера БД
    db_now = get_db_time()
    if db_now is None:
        await update.message.reply_text("Не удалось подключиться к базе данных для отладки")
        return
    
    # Получаем время в Москве
    now_msk = datetime.now(MOSCOW_TZ)
    
    # Информация о времени
    time_info = f"⏰ Время на сервере БД: {db_now}\n⏰ Московское время: {now_msk.strftime('%d.%m.%Y %H:%M:%S %z')}\n\n"
    
    # Получаем активные уведомления
    notifications = get_all_user_notifications(update.effective_user.id)
    
    if not notifications:
        await update.message.reply_text(time_info + "У вас нет уведомлений в базе данных.")
        return
    
    # Форматируем список уведомлений
    notifications_text = time_info + f"Ваши уведомления в базе данных ({len(notifications)}):\n\n"
    for i, (notification_id, notification_text, notification_time, is_sent) in enumerate(notifications, 1):
        status = "✅ Отправлено" if is_sent else "⏳ Ожидает отправки"
        notifications_text += f"{i}. ID: {notification_id}\n   Время: {notification_time}\n   Текст: {notification_text}\n   Статус: {status}\n\n"
    
    await update.message.reply_text(notifications_text)

# Команда для принудительной проверки и отправки уведомлений
async def check_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Сохраняем сообщение в БД
    save_message(update.effective_user.id, update.message.text)
    
    await update.message.reply_text("Начинаю проверку и отправку уведомлений...")
    
    # Вызываем функцию проверки уведомлений
    await check_notifications(context)
    
    await update.message.reply_text("Проверка и отправка уведомлений завершена!")

# Добавляем обработчик команды /fix для исправления устаревших уведомлений
async def fix_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Сохраняем сообщение в БД
    save_message(update.effective_user.id, update.message.text)
    
    # Исправляем часовые пояса уведомлений пользователя
    count = await fix_timezones(update.effective_user.id)
    
    if count > 0:
        await update.message.reply_text(f"Исправлено {count} уведомлений.")
    else:
        await update.message.reply_text("Все уведомления уже в правильном формате.")

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Сохраняем сообщение в БД
    save_message(update.effective_user.id, update.message.text)
    
    await update.message.reply_text(
        "Я понимаю только команды:\n"
        "/start - Начало работы с ботом\n"
        "/notify - Создать новое уведомление\n"
        "/list - Посмотреть активные уведомления\n"
        "/cancel - Отменить создание уведомления"
    )

def init_bot(token=None, run=True):
    """
    Инициализирует и запускает Telegram бота
    
    Args:
        token (str, optional): Токен Telegram бота. Если не указан, берется из конфигурации.
        run (bool, optional): Если True, бот запускается автоматически. По умолчанию True.
    
    Returns:
        application: Объект приложения бота
    """
    global _bot_app
    
    if _bot_app is not None:
        return _bot_app
    
    # Используем токен из конфигурации, если не указан явно
    if token is None:
        token = BOT_TOKEN
    
    if not token:
        logger.error("Токен бота не найден!")
        return None
    
    # Инициализация базы данных
    logger.info("Инициализация базы данных для уведомлений...")
    init_database()
    
    # Создание приложения бота
    _bot_app = Application.builder().token(token).build()
    
    # Настройка обработчиков команд
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('notify', notify)],
        states={
            WAITING_FOR_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date)],
            WAITING_FOR_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_message)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    _bot_app.add_handler(CommandHandler("start", start))
    _bot_app.add_handler(CommandHandler("list", list_notifications))
    _bot_app.add_handler(CommandHandler("debug", debug))
    _bot_app.add_handler(CommandHandler("check", check_now))
    _bot_app.add_handler(CommandHandler("fix", fix_notifications))
    _bot_app.add_handler(conv_handler)
    _bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запуск планировщика в отдельном потоке
    if run:
        # Функция для запуска планировщика уведомлений
        async def start_scheduler(app):
            await scheduled_job(app)
            
        def run_scheduler():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(start_scheduler(_bot_app))
        
        # Запуск планировщика в отдельном потоке
        scheduler_thread = Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        # Запуск бота в отдельном потоке
        def run_bot():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_bot_app.run_polling())
            
        bot_thread = Thread(target=run_bot, daemon=True)
        bot_thread.start()
        
        logger.info("Бот и планировщик уведомлений успешно запущены")
    
    return _bot_app

def create_reminder(user_id, notification_text, notification_time):
    """
    Создает новое напоминание в базе данных
    
    Args:
        user_id (int): ID пользователя Telegram
        notification_text (str): Текст уведомления
        notification_time (datetime): Время отправки уведомления (с учетом часового пояса)
    
    Returns:
        bool: True если успешно, False если произошла ошибка
    """
    try:
        # Проверка часового пояса
        if notification_time.tzinfo is None:
            # Если время без зоны, считаем что оно в московской зоне
            notification_time = MOSCOW_TZ.localize(notification_time)
        elif str(notification_time.tzinfo) != str(MOSCOW_TZ):
            # Если в другой зоне, конвертируем в московскую
            notification_time = notification_time.astimezone(MOSCOW_TZ)
        
        # Создаем уведомление в базе данных
        create_notification(user_id, notification_text, notification_time)
        
        # Логируем создание
        logger.info(f"Создано напоминание для {user_id} на {notification_time}: {notification_text}")
        return True
    except Exception as e:
        logger.error(f"Ошибка при создании напоминания: {e}")
        return False

def get_reminders(user_id):
    """
    Получает список активных напоминаний пользователя
    
    Args:
        user_id (int): ID пользователя Telegram
    
    Returns:
        list: Список активных напоминаний
    """
    try:
        reminders = get_user_notifications(user_id)
        return reminders
    except Exception as e:
        logger.error(f"Ошибка при получении напоминаний: {e}")
        return []

# Основная функция для запуска бота напрямую
def main():
    """
    Функция для запуска бота напрямую
    """
    init_bot()
    
    # Ожидаем ввод от пользователя для завершения
    print("Бот запущен! Нажмите Ctrl+C для остановки...")
    
    try:
        # Бесконечный цикл чтобы бот продолжал работать
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Бот остановлен!")

if __name__ == "__main__":
    main() 