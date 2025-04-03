#!/usr/bin/env python3
"""
Простой интерфейс для работы с системой уведомлений Telegram бота.
Позволяет легко интегрировать функцию создания уведомлений в другие приложения.

Основные функции:
- create_reminder - создать новое уведомление
- get_reminders - получить список активных уведомлений пользователя
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
import json
import logging
import psycopg2
from datetime import datetime, timedelta
import time
from threading import Thread
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import asyncio

# Загружаем переменные окружения из .env файла
load_dotenv()

# Импортируем конфигурации
from credentials.telegram.config import BOT_TOKEN
from credentials.postgres.config import HOST, PORT, DATABASE, USER, PASSWORD, BOT_PREFIX

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='simple_bot.log'
)
logger = logging.getLogger(__name__)

# Константы для состояний разговора
WAITING_FOR_DATE = 0
WAITING_FOR_MESSAGE = 1

# Таблицы в базе данных
USERS_TABLE = f"{BOT_PREFIX}users"
MESSAGES_TABLE = f"{BOT_PREFIX}messages"
NOTIFICATIONS_TABLE = f"{BOT_PREFIX}notifications"

# Московское время (UTC+3)
MOSCOW_TZ = pytz.timezone('Europe/Moscow')

# Глобальный объект для доступа к боту
_bot_app = None

# Функция для создания соединения с БД
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=HOST,
            port=PORT,
            database=DATABASE,
            user=USER,
            password=PASSWORD
        )
        return conn
    except Exception as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        return None

# Функция для инициализации базы данных
def init_database():
    conn = get_db_connection()
    if not conn:
        logger.error("Не удалось подключиться к базе данных для инициализации")
        return
    
    try:
        with conn.cursor() as cursor:
            # Создаем таблицу пользователей, если она не существует
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {USERS_TABLE} (
                    user_id NUMERIC PRIMARY KEY,
                    first_name TEXT,
                    username TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Создаем таблицу сообщений
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {MESSAGES_TABLE} (
                    id SERIAL PRIMARY KEY,
                    user_id NUMERIC,
                    message_text TEXT,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Создаем таблицу уведомлений
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {NOTIFICATIONS_TABLE} (
                    id SERIAL PRIMARY KEY,
                    user_id NUMERIC,
                    notification_text TEXT,
                    notification_time TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    is_sent BOOLEAN DEFAULT FALSE
                )
            """)
            
            conn.commit()
            logger.info("Таблицы в базе данных успешно созданы")
    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка при инициализации базы данных: {e}")
    finally:
        conn.close()

# Функция для сохранения пользователя в БД
def save_user(user_id, first_name, username):
    conn = get_db_connection()
    if not conn:
        logger.error("Не удалось подключиться к базе данных для сохранения пользователя")
        return
    
    try:
        with conn.cursor() as cursor:
            # Проверяем, существует ли пользователь
            cursor.execute(
                f"SELECT user_id FROM {USERS_TABLE} WHERE user_id = %s",
                (user_id,)
            )
            if cursor.fetchone() is None:
                # Если пользователя нет, то добавляем его
                cursor.execute(
                    f"INSERT INTO {USERS_TABLE} (user_id, first_name, username) VALUES (%s, %s, %s)",
                    (user_id, first_name, username)
                )
                conn.commit()
                logger.info(f"Новый пользователь добавлен: {user_id}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка при сохранении пользователя: {e}")
    finally:
        conn.close()

# Функция для сохранения сообщения в БД
def save_message(user_id, message_text):
    conn = get_db_connection()
    if not conn:
        logger.error("Не удалось подключиться к базе данных для сохранения сообщения")
        return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO {MESSAGES_TABLE} (user_id, message_text) VALUES (%s, %s)",
                (user_id, message_text)
            )
            conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка при сохранении сообщения: {e}")
    finally:
        conn.close()

# Функция для создания уведомления в БД
def create_notification(user_id, message, notification_time):
    conn = get_db_connection()
    if not conn:
        logger.error("Не удалось подключиться к базе данных для создания уведомления")
        return
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO {NOTIFICATIONS_TABLE} (user_id, notification_text, notification_time) VALUES (%s, %s, %s) RETURNING id",
                (user_id, message, notification_time)
            )
            notification_id = cursor.fetchone()[0]
            conn.commit()
            logger.info(f"Создано новое уведомление #{notification_id} для пользователя {user_id} на {notification_time.strftime('%d.%m.%Y %H:%M:%S %z')}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка при создании уведомления: {e}")
    finally:
        conn.close()

# Функция для получения активных уведомлений пользователя
def get_user_notifications(user_id):
    conn = get_db_connection()
    if not conn:
        logger.error("Не удалось подключиться к базе данных для получения уведомлений")
        return []
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"SELECT id, notification_text, notification_time FROM {NOTIFICATIONS_TABLE} WHERE user_id = %s AND is_sent = FALSE ORDER BY notification_time",
                (user_id,)
            )
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Ошибка при получении уведомлений пользователя: {e}")
        return []
    finally:
        conn.close()

# Функция для проверки и отправки уведомлений
async def check_notifications(context):
    now = datetime.now(MOSCOW_TZ)
    logger.info(f"Проверка уведомлений в {now.strftime('%d.%m.%Y %H:%M:%S %z')}")
    conn = get_db_connection()
    
    if not conn:
        logger.error("Не удалось подключиться к базе данных для проверки уведомлений")
        return
    
    try:
        with conn.cursor() as cursor:
            # Выводим все активные уведомления для отладки
            cursor.execute(
                f"SELECT id, user_id, notification_text, notification_time, is_sent FROM {NOTIFICATIONS_TABLE} WHERE is_sent = FALSE"
            )
            all_notifications = cursor.fetchall()
            logger.info(f"Всего активных уведомлений в базе: {len(all_notifications)}")
            for n in all_notifications:
                logger.info(f"Активное уведомление: ID={n[0]}, user_id={n[1]}, text={n[2]}, time={n[3]}, is_sent={n[4]}")
            
            # Находим все неотправленные уведомления, время которых настало
            query = f"""
                SELECT id, user_id, notification_text 
                FROM {NOTIFICATIONS_TABLE} 
                WHERE 
                    is_sent = FALSE AND 
                    notification_time <= %s
            """
            # Используем текущее время для сравнения
            params = (now,)
            logger.info(f"Запрос для поиска уведомлений: {query} с параметрами {params}")
            
            cursor.execute(query, params)
            
            notifications = cursor.fetchall()
            logger.info(f"Найдено {len(notifications)} уведомлений для отправки")
            
            for notification_id, user_id, notification_text in notifications:
                try:
                    # Преобразуем Decimal в int для отправки
                    user_id_int = int(user_id)
                    
                    # Отправляем уведомление
                    await context.bot.send_message(
                        chat_id=user_id_int,
                        text=f"🔔 Напоминание: {notification_text}"
                    )
                    
                    # Помечаем уведомление как отправленное
                    cursor.execute(
                        f"UPDATE {NOTIFICATIONS_TABLE} SET is_sent = TRUE WHERE id = %s",
                        (notification_id,)
                    )
                    logger.info(f"Уведомление {notification_id} отправлено пользователю {user_id}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке уведомления {notification_id}: {e}")
            
            if notifications:
                conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка при проверке и отправке уведомлений: {e}")
    finally:
        conn.close()

# Функция для запуска проверки уведомлений в фоне
async def scheduled_job(context):
    while True:
        try:
            # Ждем до начала следующей минуты
            now = datetime.now(MOSCOW_TZ)
            next_minute = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
            seconds_to_wait = (next_minute - now).total_seconds()
            
            logger.info(f"Ожидание {seconds_to_wait:.2f} секунд до следующей проверки в {next_minute.strftime('%H:%M:%S')}")
            
            # Спим до следующей минуты
            await asyncio.sleep(max(0, seconds_to_wait))
            
            # Проверяем уведомления
            await check_notifications(context)
        except Exception as e:
            logger.error(f"Ошибка в планировщике: {e}")
            # Продолжаем работу даже при ошибке
            await asyncio.sleep(60)

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
    
    conn = get_db_connection()
    if not conn:
        await update.message.reply_text("Не удалось подключиться к базе данных для отладки")
        return
    
    try:
        with conn.cursor() as cursor:
            # Получаем текущее время сервера
            cursor.execute("SELECT NOW()")
            db_now = cursor.fetchone()[0]
            
            # Получаем время в Москве
            now_msk = datetime.now(MOSCOW_TZ)
            
            # Информация о времени
            time_info = f"⏰ Время на сервере БД: {db_now}\n⏰ Московское время: {now_msk.strftime('%d.%m.%Y %H:%M:%S %z')}\n\n"
            
            # Получаем активные уведомления
            cursor.execute(
                f"SELECT id, user_id, notification_text, notification_time, is_sent FROM {NOTIFICATIONS_TABLE} WHERE user_id = %s ORDER BY notification_time",
                (update.effective_user.id,)
            )
            notifications = cursor.fetchall()
            
            if not notifications:
                await update.message.reply_text(time_info + "У вас нет уведомлений в базе данных.")
                return
            
            # Форматируем список уведомлений
            notifications_text = time_info + f"Ваши уведомления в базе данных ({len(notifications)}):\n\n"
            for i, (notification_id, user_id, notification_text, notification_time, is_sent) in enumerate(notifications, 1):
                status = "✅ Отправлено" if is_sent else "⏳ Ожидает отправки"
                notifications_text += f"{i}. ID: {notification_id}\n   Время: {notification_time}\n   Текст: {notification_text}\n   Статус: {status}\n\n"
            
            await update.message.reply_text(notifications_text)
    except Exception as e:
        logger.error(f"Ошибка при отладке: {e}")
        await update.message.reply_text(f"Произошла ошибка при отладке: {e}")
    finally:
        conn.close()

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
    
    conn = get_db_connection()
    if not conn:
        await update.message.reply_text("Не удалось подключиться к базе данных для исправления уведомлений")
        return
    
    try:
        with conn.cursor() as cursor:
            # Находим все неотправленные уведомления
            cursor.execute(
                f"SELECT id, notification_time FROM {NOTIFICATIONS_TABLE} WHERE is_sent = FALSE"
            )
            notifications = cursor.fetchall()
            
            if not notifications:
                await update.message.reply_text("Нет активных уведомлений для исправления.")
                return
            
            count = 0
            for notification_id, notification_time in notifications:
                # Проверяем часовой пояс
                if notification_time.tzinfo is None or str(notification_time.tzinfo) != str(MOSCOW_TZ):
                    # Если время не в московской зоне, конвертируем его
                    if notification_time.tzinfo is None:
                        # Время без зоны - считаем, что оно в UTC
                        utc_time = notification_time.replace(tzinfo=pytz.UTC)
                        msk_time = utc_time.astimezone(MOSCOW_TZ)
                    else:
                        # Время с другой зоной - конвертируем в московскую
                        msk_time = notification_time.astimezone(MOSCOW_TZ)
                    
                    # Обновляем время в базе
                    cursor.execute(
                        f"UPDATE {NOTIFICATIONS_TABLE} SET notification_time = %s WHERE id = %s",
                        (msk_time, notification_id)
                    )
                    count += 1
            
            if count > 0:
                conn.commit()
                await update.message.reply_text(f"Исправлено {count} уведомлений.")
            else:
                await update.message.reply_text("Все уведомления уже в правильном формате.")
    
    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка при исправлении уведомлений: {e}")
        await update.message.reply_text(f"Произошла ошибка при исправлении уведомлений: {e}")
    finally:
        conn.close()

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