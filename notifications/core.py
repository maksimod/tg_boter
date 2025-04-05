"""
Core functionality for the Telegram notification bot.
This module contains the implementation of notification handlers and conversation flow.
"""

import logging
import asyncio
import traceback
import sys
from threading import Thread
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

# Import database functions
from base.db import (
    MOSCOW_TZ, init_database, save_user, save_message, create_notification,
    get_user_notifications, get_db_time, get_all_user_notifications
)

# Import notification functions
from notifications import check_notifications, scheduled_job, fix_timezones

# Set up logging
logger = logging.getLogger(__name__)

# Установка уровня логирования для модуля
logger.setLevel(logging.DEBUG)

# Добавление обработчика для вывода в консоль
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Добавляем обработчик к логгеру, если его еще нет
if not logger.handlers:
    logger.addHandler(console_handler)
    
    # Добавляем также обработчик для записи в файл
    file_handler = logging.FileHandler('log/notifications_core.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

# Constants for conversation states
WAITING_FOR_DATE = 0
WAITING_FOR_MESSAGE = 1

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command"""
    try:
        user = update.effective_user
        logger.debug(f"Обработка команды /start от пользователя {user.id} ({user.first_name}, @{user.username})")
        
        # Save user to database
        logger.debug(f"Сохранение пользователя {user.id} в базу данных")
        save_user(user.id, user.first_name, user.username)
        
        logger.debug(f"Отправка приветственного сообщения пользователю {user.id}")
        await update.message.reply_text(
            f"Привет, {user.first_name}! Я бот для создания уведомлений.\n\n"
            "Чтобы создать новое уведомление, используйте команду /notify.\n"
            "Чтобы посмотреть все активные уведомления, используйте команду /list."
        )
        logger.info(f"Пользователь {user.id} успешно запустил бота")
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Ошибка в обработчике /start: {e}")
        logger.error(f"Трассировка ошибки: {error_traceback}")
        try:
            await update.message.reply_text("Произошла ошибка при обработке команды. Пожалуйста, попробуйте позже.")
        except:
            pass

async def notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the notification creation process"""
    try:
        user_id = update.effective_user.id
        logger.debug(f"Пользователь {user_id} начал создание нового уведомления (команда /notify)")
        
        # Save message to database
        logger.debug(f"Сохранение сообщения от пользователя {user_id} в базу данных")
        save_message(user_id, update.message.text)
        
        logger.debug(f"Запрос даты и времени у пользователя {user_id}")
        await update.message.reply_text(
            "Пожалуйста, введите дату и время уведомления в формате ДД.ММ.ГГ ЧЧ:ММ\n"
            "Например: 03.04.25 16:45"
        )
        logger.debug(f"Переход в состояние WAITING_FOR_DATE для пользователя {user_id}")
        return WAITING_FOR_DATE
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Ошибка в обработчике /notify: {e}")
        logger.error(f"Трассировка ошибки: {error_traceback}")
        try:
            await update.message.reply_text("Произошла ошибка при создании уведомления. Пожалуйста, попробуйте позже.")
        except:
            pass
        return ConversationHandler.END

async def get_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle date input for notification"""
    try:
        user_id = update.effective_user.id
        logger.debug(f"Обработка ввода даты от пользователя {user_id}")
        
        # Save message to database
        save_message(user_id, update.message.text)
        
        date_str = update.message.text.strip()
        logger.debug(f"Пользователь {user_id} ввел дату: '{date_str}'")
        
        try:
            # Parse date and time from user input
            logger.debug(f"Попытка парсинга даты '{date_str}' в формате '%d.%m.%y %H:%M'")
            notification_time = datetime.strptime(date_str, "%d.%m.%y %H:%M")
            # Add timezone information
            notification_time = MOSCOW_TZ.localize(notification_time)
            logger.debug(f"Дата успешно преобразована: {notification_time}")
            
            # Check that date is not in the past
            now = datetime.now(MOSCOW_TZ)
            logger.debug(f"Проверка, что дата не в прошлом: {notification_time} > {now}")
            
            if notification_time <= now:
                logger.debug(f"Пользователь {user_id} ввел прошедшую дату")
                await update.message.reply_text("Указанная дата и время уже прошли. Пожалуйста, введите будущую дату и время.")
                return WAITING_FOR_DATE
            
            # Save date in context
            logger.debug(f"Сохранение даты {notification_time} в контексте для пользователя {user_id}")
            context.user_data['notification_time'] = notification_time
            
            logger.debug(f"Запрос текста уведомления у пользователя {user_id}")
            await update.message.reply_text(
                f"Уведомление будет отправлено {notification_time.strftime('%d.%m.%Y в %H:%M')} (МСК).\n"
                f"Теперь введите текст уведомления:"
            )
            logger.debug(f"Переход в состояние WAITING_FOR_MESSAGE для пользователя {user_id}")
            return WAITING_FOR_MESSAGE
        except ValueError:
            logger.debug(f"Пользователь {user_id} ввел дату в неверном формате: '{date_str}'")
            await update.message.reply_text(
                "Неверный формат даты. Пожалуйста, используйте формат ДД.ММ.ГГ ЧЧ:ММ\n"
                "Например: 03.04.25 16:45"
            )
            return WAITING_FOR_DATE
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Ошибка в обработчике get_date: {e}")
        logger.error(f"Трассировка ошибки: {error_traceback}")
        try:
            await update.message.reply_text("Произошла ошибка при обработке даты. Пожалуйста, попробуйте позже.")
        except:
            pass
        return ConversationHandler.END

async def get_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle message input for notification"""
    try:
        user_id = update.effective_user.id
        logger.debug(f"Обработка ввода текста уведомления от пользователя {user_id}")
        
        # Save message to database
        save_message(user_id, update.message.text)
        
        message_text = update.message.text.strip()
        logger.debug(f"Пользователь {user_id} ввел текст: '{message_text}'")
        
        notification_time = context.user_data.get('notification_time')
        if not notification_time:
            logger.error(f"Для пользователя {user_id} не найдено время уведомления в контексте")
            await update.message.reply_text("Произошла ошибка. Пожалуйста, начните создание уведомления заново с команды /notify.")
            return ConversationHandler.END
        
        # Log notification parameters
        logger.info(f"Создание уведомления для пользователя {user_id} на {notification_time.strftime('%d.%m.%Y %H:%M')} с текстом: {message_text}")
        
        # Create notification in database
        logger.debug(f"Сохранение уведомления в базу данных для пользователя {user_id}")
        create_notification(user_id, message_text, notification_time)
        
        # Current Moscow time for comparison
        now = datetime.now(MOSCOW_TZ)
        time_diff = notification_time - now
        hours, remainder = divmod(time_diff.total_seconds(), 3600)
        minutes, _ = divmod(remainder, 60)
        time_str = f"{int(hours)} ч {int(minutes)} мин"
        
        logger.debug(f"Отправка подтверждения создания уведомления пользователю {user_id}")
        await update.message.reply_text(
            f"Уведомление создано! {notification_time.strftime('%d.%m.%Y в %H:%M')} (МСК) "
            f"вы получите сообщение: \"{message_text}\"\n\n"
            f"До уведомления осталось: {time_str}"
        )
        
        # Clear user data
        logger.debug(f"Очистка данных пользователя {user_id} в контексте")
        context.user_data.clear()
        
        logger.info(f"Пользователь {user_id} успешно создал уведомление на {notification_time}")
        return ConversationHandler.END
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Ошибка в обработчике get_message: {e}")
        logger.error(f"Трассировка ошибки: {error_traceback}")
        try:
            await update.message.reply_text("Произошла ошибка при создании уведомления. Пожалуйста, попробуйте позже.")
        except:
            pass
        return ConversationHandler.END

async def list_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all active notifications for the user"""
    try:
        user_id = update.effective_user.id
        logger.debug(f"Обработка команды /list от пользователя {user_id}")
        
        # Save message to database
        save_message(user_id, update.message.text)
        
        # Get user notifications
        logger.debug(f"Получение списка уведомлений для пользователя {user_id}")
        user_notifications = get_user_notifications(user_id)
        
        if not user_notifications:
            logger.debug(f"У пользователя {user_id} нет активных уведомлений")
            await update.message.reply_text("У вас нет активных уведомлений.")
            return
        
        # Format notification list
        logger.debug(f"Найдено {len(user_notifications)} активных уведомлений для пользователя {user_id}")
        notifications_text = "Ваши активные уведомления:\n\n"
        for i, (notification_id, notification_text, notification_time) in enumerate(user_notifications, 1):
            notifications_text += f"{i}. {notification_time.strftime('%d.%m.%Y %H:%M')} - {notification_text}\n"
        
        logger.debug(f"Отправка списка уведомлений пользователю {user_id}")
        await update.message.reply_text(notifications_text)
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Ошибка в обработчике /list: {e}")
        logger.error(f"Трассировка ошибки: {error_traceback}")
        try:
            await update.message.reply_text("Произошла ошибка при получении списка уведомлений. Пожалуйста, попробуйте позже.")
        except:
            pass

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel notification creation"""
    try:
        user_id = update.effective_user.id
        logger.debug(f"Обработка команды /cancel от пользователя {user_id}")
        
        # Save message to database
        save_message(user_id, update.message.text)
        
        logger.debug(f"Очистка данных пользователя {user_id} в контексте")
        context.user_data.clear()
        
        logger.debug(f"Отправка сообщения об отмене пользователю {user_id}")
        await update.message.reply_text("Создание уведомления отменено.")
        
        logger.info(f"Пользователь {user_id} отменил создание уведомления")
        return ConversationHandler.END
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Ошибка в обработчике /cancel: {e}")
        logger.error(f"Трассировка ошибки: {error_traceback}")
        return ConversationHandler.END

async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show debug information"""
    try:
        user_id = update.effective_user.id
        logger.debug(f"Обработка команды /debug от пользователя {user_id}")
        
        # Save message to database
        save_message(user_id, update.message.text)
        
        # Get current time from DB
        logger.debug("Получение текущего времени из базы данных")
        db_now = get_db_time()
        if db_now is None:
            logger.error("Не удалось получить время из базы данных")
            await update.message.reply_text("Не удалось подключиться к базе данных для отладки")
            return
        
        # Get Moscow time
        now_msk = datetime.now(MOSCOW_TZ)
        logger.debug(f"Время БД: {db_now}, Московское время: {now_msk}")
        
        # Time information
        time_info = f"⏰ Время на сервере БД: {db_now}\n⏰ Московское время: {now_msk.strftime('%d.%m.%Y %H:%M:%S %z')}\n\n"
        
        # Get active notifications
        logger.debug(f"Получение всех уведомлений пользователя {user_id}")
        notifications = get_all_user_notifications(user_id)
        
        if not notifications:
            logger.debug(f"У пользователя {user_id} нет уведомлений в базе данных")
            await update.message.reply_text(time_info + "У вас нет уведомлений в базе данных.")
            return
        
        # Format notification list
        logger.debug(f"Найдено {len(notifications)} уведомлений для пользователя {user_id}")
        notifications_text = time_info + f"Ваши уведомления в базе данных ({len(notifications)}):\n\n"
        for i, (notification_id, notification_text, notification_time, is_sent) in enumerate(notifications, 1):
            status = "✅ Отправлено" if is_sent else "⏳ Ожидает отправки"
            notifications_text += f"{i}. ID: {notification_id}\n   Время: {notification_time}\n   Текст: {notification_text}\n   Статус: {status}\n\n"
        
        logger.debug(f"Отправка отладочной информации пользователю {user_id}")
        await update.message.reply_text(notifications_text)
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Ошибка в обработчике /debug: {e}")
        logger.error(f"Трассировка ошибки: {error_traceback}")
        try:
            await update.message.reply_text("Произошла ошибка при получении отладочной информации. Пожалуйста, попробуйте позже.")
        except:
            pass

async def check_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force check and send notifications"""
    try:
        user_id = update.effective_user.id
        logger.debug(f"Обработка команды /check от пользователя {user_id}")
        
        # Save message to database
        save_message(user_id, update.message.text)
        
        logger.debug(f"Отправка сообщения о начале проверки пользователю {user_id}")
        await update.message.reply_text("Начинаю проверку и отправку уведомлений...")
        
        # Call the notification check function
        logger.debug("Вызов функции check_notifications для принудительной проверки")
        await check_notifications(context)
        
        logger.debug(f"Отправка сообщения о завершении проверки пользователю {user_id}")
        await update.message.reply_text("Проверка и отправка уведомлений завершена!")
        
        logger.info(f"Пользователь {user_id} выполнил принудительную проверку уведомлений")
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Ошибка в обработчике /check: {e}")
        logger.error(f"Трассировка ошибки: {error_traceback}")
        try:
            await update.message.reply_text("Произошла ошибка при проверке уведомлений. Пожалуйста, попробуйте позже.")
        except:
            pass

async def fix_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fix notification timezones"""
    try:
        user_id = update.effective_user.id
        logger.debug(f"Обработка команды /fix от пользователя {user_id}")
        
        # Save message to database
        save_message(user_id, update.message.text)
        
        # Fix timezone issues for the user's notifications
        logger.debug(f"Вызов функции fix_timezones для пользователя {user_id}")
        count = await fix_timezones(user_id)
        
        if count > 0:
            logger.info(f"Исправлено {count} уведомлений для пользователя {user_id}")
            await update.message.reply_text(f"Исправлено {count} уведомлений.")
        else:
            logger.debug(f"Для пользователя {user_id} все уведомления уже в правильном формате")
            await update.message.reply_text("Все уведомления уже в правильном формате.")
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Ошибка в обработчике /fix: {e}")
        logger.error(f"Трассировка ошибки: {error_traceback}")
        try:
            await update.message.reply_text("Произошла ошибка при исправлении часовых поясов. Пожалуйста, попробуйте позже.")
        except:
            pass

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    try:
        user_id = update.effective_user.id
        message_text = update.message.text
        logger.debug(f"Получено текстовое сообщение от пользователя {user_id}: '{message_text}'")
        
        # Save message to database
        save_message(user_id, message_text)
        
        logger.debug(f"Отправка сообщения с доступными командами пользователю {user_id}")
        await update.message.reply_text(
            "Я понимаю только команды:\n"
            "/start - Начало работы с ботом\n"
            "/notify - Создать новое уведомление\n"
            "/list - Посмотреть активные уведомления\n"
            "/cancel - Отменить создание уведомления"
        )
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Ошибка в обработчике текстовых сообщений: {e}")
        logger.error(f"Трассировка ошибки: {error_traceback}")

def setup_handlers(application):
    """Set up all command handlers for the bot"""
    try:
        logger.info("Настройка обработчиков команд бота")
        
        # Create conversation handler for notification creation
        logger.debug("Создание обработчика диалога для создания уведомлений")
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('notify', notify)],
            states={
                WAITING_FOR_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date)],
                WAITING_FOR_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_message)]
            },
            fallbacks=[CommandHandler('cancel', cancel)]
        )
        
        # Add all handlers
        logger.debug("Добавление обработчиков команд")
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("list", list_notifications))
        application.add_handler(CommandHandler("debug", debug))
        application.add_handler(CommandHandler("check", check_now))
        application.add_handler(CommandHandler("fix", fix_notifications))
        application.add_handler(conv_handler)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        logger.info("Обработчики команд бота успешно настроены")
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Ошибка при настройке обработчиков команд: {e}")
        logger.error(f"Трассировка ошибки: {error_traceback}")
        raise

def start_scheduler(bot_app):
    """Start the notification scheduler in a separate thread"""
    try:
        logger.info("Запуск планировщика уведомлений")
        
        async def run_scheduler(app):
            logger.debug("Запуск асинхронной функции планировщика")
            try:
                await scheduled_job(app)
            except Exception as e:
                error_traceback = traceback.format_exc()
                logger.error(f"Ошибка в асинхронной функции планировщика: {e}")
                logger.error(f"Трассировка ошибки: {error_traceback}")
        
        def scheduler_thread_func():
            try:
                logger.debug("Инициализация event loop для планировщика")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                logger.debug("Запуск планировщика в отдельном потоке")
                loop.run_until_complete(run_scheduler(bot_app))
            except Exception as e:
                error_traceback = traceback.format_exc()
                logger.error(f"Ошибка в потоке планировщика: {e}")
                logger.error(f"Трассировка ошибки: {error_traceback}")
        
        logger.debug("Создание и запуск потока планировщика")
        scheduler_thread = Thread(target=scheduler_thread_func, daemon=True)
        scheduler_thread.start()
        
        logger.info(f"Планировщик уведомлений успешно запущен в отдельном потоке (ID: {scheduler_thread.ident})")
        return scheduler_thread
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Ошибка при запуске планировщика: {e}")
        logger.error(f"Трассировка ошибки: {error_traceback}")
        raise

def start_bot_polling(bot_app):
    """Start the bot polling in a separate thread"""
    try:
        logger.info("Запуск бота в режиме polling")
        
        def bot_thread_func():
            try:
                logger.debug("Инициализация event loop для бота")
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                logger.debug("Запуск polling бота в отдельном потоке")
                loop.run_until_complete(bot_app.run_polling())
            except Exception as e:
                error_traceback = traceback.format_exc()
                logger.error(f"Ошибка в потоке бота: {e}")
                logger.error(f"Трассировка ошибки: {error_traceback}")
        
        logger.debug("Создание и запуск потока бота")
        bot_thread = Thread(target=bot_thread_func, daemon=True)
        bot_thread.start()
        
        logger.info(f"Бот успешно запущен в отдельном потоке (ID: {bot_thread.ident})")
        return bot_thread
    except Exception as e:
        error_traceback = traceback.format_exc()
        logger.error(f"Ошибка при запуске бота: {e}")
        logger.error(f"Трассировка ошибки: {error_traceback}")
        raise 