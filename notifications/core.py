"""
Core functionality for the Telegram notification bot.
This module contains the implementation of notification handlers and conversation flow.
"""

import logging
import asyncio
from threading import Thread
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

# Import database functions
from database import (
    MOSCOW_TZ, init_database, save_user, save_message, create_notification,
    get_user_notifications, get_db_time, get_all_user_notifications
)

# Import notification functions
from notifications import check_notifications, scheduled_job, fix_timezones

# Set up logging
logger = logging.getLogger(__name__)

# Constants for conversation states
WAITING_FOR_DATE = 0
WAITING_FOR_MESSAGE = 1

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command"""
    user = update.effective_user
    
    # Save user to database
    save_user(user.id, user.first_name, user.username)
    
    await update.message.reply_text(
        f"Привет, {user.first_name}! Я бот для создания уведомлений.\n\n"
        "Чтобы создать новое уведомление, используйте команду /notify.\n"
        "Чтобы посмотреть все активные уведомления, используйте команду /list."
    )

async def notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the notification creation process"""
    # Save message to database
    save_message(update.effective_user.id, update.message.text)
    
    await update.message.reply_text(
        "Пожалуйста, введите дату и время уведомления в формате ДД.ММ.ГГ ЧЧ:ММ\n"
        "Например: 03.04.25 16:45"
    )
    return WAITING_FOR_DATE

async def get_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle date input for notification"""
    # Save message to database
    save_message(update.effective_user.id, update.message.text)
    
    date_str = update.message.text.strip()
    try:
        # Parse date and time from user input
        notification_time = datetime.strptime(date_str, "%d.%m.%y %H:%M")
        # Add timezone information
        notification_time = MOSCOW_TZ.localize(notification_time)
        
        # Check that date is not in the past
        now = datetime.now(MOSCOW_TZ)
        if notification_time <= now:
            await update.message.reply_text("Указанная дата и время уже прошли. Пожалуйста, введите будущую дату и время.")
            return WAITING_FOR_DATE
        
        # Save date in context
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

async def get_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle message input for notification"""
    # Save message to database
    save_message(update.effective_user.id, update.message.text)
    
    message_text = update.message.text.strip()
    notification_time = context.user_data['notification_time']
    
    # Log notification parameters
    logger.info(f"Создание уведомления для пользователя {update.effective_user.id} на {notification_time.strftime('%d.%m.%Y %H:%M')} с текстом: {message_text}")
    
    # Create notification in database
    create_notification(update.effective_user.id, message_text, notification_time)
    
    # Current Moscow time for comparison
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
    
    # Clear user data
    context.user_data.clear()
    
    return ConversationHandler.END

async def list_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all active notifications for the user"""
    # Save message to database
    save_message(update.effective_user.id, update.message.text)
    
    # Get user notifications
    user_notifications = get_user_notifications(update.effective_user.id)
    
    if not user_notifications:
        await update.message.reply_text("У вас нет активных уведомлений.")
        return
    
    # Format notification list
    notifications_text = "Ваши активные уведомления:\n\n"
    for i, (notification_id, notification_text, notification_time) in enumerate(user_notifications, 1):
        notifications_text += f"{i}. {notification_time.strftime('%d.%m.%Y %H:%M')} - {notification_text}\n"
    
    await update.message.reply_text(notifications_text)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel notification creation"""
    # Save message to database
    save_message(update.effective_user.id, update.message.text)
    
    context.user_data.clear()
    await update.message.reply_text("Создание уведомления отменено.")
    return ConversationHandler.END

async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show debug information"""
    # Save message to database
    save_message(update.effective_user.id, update.message.text)
    
    # Get current time from DB
    db_now = get_db_time()
    if db_now is None:
        await update.message.reply_text("Не удалось подключиться к базе данных для отладки")
        return
    
    # Get Moscow time
    now_msk = datetime.now(MOSCOW_TZ)
    
    # Time information
    time_info = f"⏰ Время на сервере БД: {db_now}\n⏰ Московское время: {now_msk.strftime('%d.%m.%Y %H:%M:%S %z')}\n\n"
    
    # Get active notifications
    notifications = get_all_user_notifications(update.effective_user.id)
    
    if not notifications:
        await update.message.reply_text(time_info + "У вас нет уведомлений в базе данных.")
        return
    
    # Format notification list
    notifications_text = time_info + f"Ваши уведомления в базе данных ({len(notifications)}):\n\n"
    for i, (notification_id, notification_text, notification_time, is_sent) in enumerate(notifications, 1):
        status = "✅ Отправлено" if is_sent else "⏳ Ожидает отправки"
        notifications_text += f"{i}. ID: {notification_id}\n   Время: {notification_time}\n   Текст: {notification_text}\n   Статус: {status}\n\n"
    
    await update.message.reply_text(notifications_text)

async def check_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force check and send notifications"""
    # Save message to database
    save_message(update.effective_user.id, update.message.text)
    
    await update.message.reply_text("Начинаю проверку и отправку уведомлений...")
    
    # Call the notification check function
    await check_notifications(context)
    
    await update.message.reply_text("Проверка и отправка уведомлений завершена!")

async def fix_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fix notification timezones"""
    # Save message to database
    save_message(update.effective_user.id, update.message.text)
    
    # Fix timezone issues for the user's notifications
    count = await fix_timezones(update.effective_user.id)
    
    if count > 0:
        await update.message.reply_text(f"Исправлено {count} уведомлений.")
    else:
        await update.message.reply_text("Все уведомления уже в правильном формате.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    # Save message to database
    save_message(update.effective_user.id, update.message.text)
    
    await update.message.reply_text(
        "Я понимаю только команды:\n"
        "/start - Начало работы с ботом\n"
        "/notify - Создать новое уведомление\n"
        "/list - Посмотреть активные уведомления\n"
        "/cancel - Отменить создание уведомления"
    )

def setup_handlers(application):
    """Set up all command handlers for the bot"""
    # Create conversation handler for notification creation
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('notify', notify)],
        states={
            WAITING_FOR_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date)],
            WAITING_FOR_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_message)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # Add all handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list", list_notifications))
    application.add_handler(CommandHandler("debug", debug))
    application.add_handler(CommandHandler("check", check_now))
    application.add_handler(CommandHandler("fix", fix_notifications))
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

def start_scheduler(bot_app):
    """Start the notification scheduler in a separate thread"""
    async def run_scheduler(app):
        await scheduled_job(app)
        
    def scheduler_thread_func():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_scheduler(bot_app))
    
    scheduler_thread = Thread(target=scheduler_thread_func, daemon=True)
    scheduler_thread.start()
    return scheduler_thread

def start_bot_polling(bot_app):
    """Start the bot polling in a separate thread"""
    def bot_thread_func():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(bot_app.run_polling())
        
    bot_thread = Thread(target=bot_thread_func, daemon=True)
    bot_thread.start()
    return bot_thread 