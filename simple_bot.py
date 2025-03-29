from easy_bot import (
    write_translated_message, 
    button, 
    message_with_buttons, 
    on_start, 
    on_callback, 
    on_text_message,
    run_bot,
    add_notification_to_db,
    get_user_notifications,
    mark_notification_as_sent,
    delete_notification,
    get_active_notifications
)
import asyncpg
import asyncio
import sys
import os
import importlib.util

# Импортируем конфигурацию PostgreSQL
sys.path.append(os.path.join(os.path.dirname(__file__), 'credentials', 'postgres'))
try:
    # Формируем полный путь к файлу config.py (без точки)
    config_path = os.path.join(os.path.dirname(__file__), 'credentials', 'postgres', 'config.py')
    
    # Загружаем модуль напрямую по пути
    spec = importlib.util.spec_from_file_location("postgres_config", config_path)
    postgres_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(postgres_config)
    
    print(f"Загружена конфигурация PostgreSQL из файла {config_path}")
except Exception as e:
    print(f"Ошибка: не удалось загрузить файл конфигурации credentials/postgres/config.py: {str(e)}")
    postgres_config = None

# Токен загрузится автоматически из credentials/telegram/token.txt
BOT_TOKEN = None

# Глобальная переменная для соединения с БД
db_connection = None

# Функция для инициализации PostgreSQL
async def init_postgres():
    global db_connection
    try:
        if postgres_config:
            # Закрываем предыдущее соединение, если оно было
            if db_connection:
                await db_connection.close()
                
            # Только допустимые параметры подключения PostgreSQL
            valid_pg_params = {
                'user', 'password', 'database', 'host', 'port', 
                'username', 'dbname', 'server', 'server_port'
            }
                
            # Создаем новое соединение - собираем параметры из всех возможных мест
            conn_params = {}
            
            # Собираем все атрибуты из модуля config
            for key, value in vars(postgres_config).items():
                # Пропускаем служебные атрибуты и None-значения
                if key.startswith('__') or value is None:
                    continue
                    
                # Приводим ключ к нижнему регистру для нормализации
                key_lower = key.lower()
                
                # Проверяем, есть ли этот параметр в списке допустимых
                if key_lower in valid_pg_params:
                    conn_params[key_lower] = value
                    
                # Проверяем специальные параметры с префиксами
                elif key_lower.startswith('db_') or key_lower.startswith('pg_'):
                    # Удаляем префикс
                    clean_key = key_lower.replace('db_', '').replace('pg_', '')
                    if clean_key in valid_pg_params:
                        conn_params[clean_key] = value
                
            # Отображаем найденные параметры
            print(f"Найдены параметры PostgreSQL: {conn_params}")
            
            # Если параметров нет, возвращаем ошибку
            if not conn_params:
                print("Ошибка: в файле конфигурации нет параметров для подключения к БД")
                return None
                
            # Создаем новое соединение
            db_connection = await asyncpg.connect(**conn_params)
            print("PostgreSQL успешно инициализирован")
            
            # Создаем таблицу уведомлений, если её нет
            await db_connection.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    text TEXT NOT NULL,
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    is_sent BOOLEAN DEFAULT FALSE
                )
            ''')
            print("Таблица уведомлений проверена/создана")
            
            return db_connection
        else:
            print("Ошибка: отсутствует конфигурация PostgreSQL")
            return None
    except Exception as e:
        print(f"Ошибка при инициализации PostgreSQL: {str(e)}")
        return None

# Временное решение для получения ID пользователя
async def get_user_id():
    # Возвращаем фиксированный ID, чтобы избежать ошибок
    # В реальном боте это должно быть заменено на получение реального ID пользователя
    return 123456  # Используем фиксированный ID для всех пользователей

# Обработчик команды /start
@on_start
async def handle_start():
    # Пытаемся инициализировать PostgreSQL при старте
    try:
        await init_postgres()
    except Exception as e:
        print(f"Ошибка при инициализации БД в handle_start: {str(e)}")
    
    await message_with_buttons("Добро пожаловать в бота! Выберите действие:", [
        [["🔍 Поиск информации", "search_info"], ["📅 Создать напоминание", "create_notification"]],
        [["📋 Мои напоминания", "list_notifications"], ["🔔 Проверить напоминания", "check_notifications"]],
        [["ℹ️ О боте", "about"]]
    ])

# Обработчики callback-кнопок
@on_callback("info")
async def handle_info():
    await write_translated_message("Это информационное сообщение.")
    await button([
        ["Узнать больше", "info_more"],
        ["Вернуться в меню", "back_to_menu"]
    ])

@on_callback("info_more")
async def handle_info_more():
    await write_translated_message("Я могу создавать напоминания и работать на разных языках.")
    await button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@on_callback("help")
async def handle_help():
    await write_translated_message("Используйте кнопки для навигации и создания напоминаний.")
    await button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@on_callback("about")
async def handle_about():
    await write_translated_message("Это бот с напоминаниями и поддержкой нескольких языков.")
    await button([
        ["Вернуться в меню", "back_to_menu"]
    ])

@on_callback("exit")
async def handle_exit():
    await write_translated_message("До свидания! Используйте /start для запуска.")

@on_callback("back_to_menu")
async def handle_back():
    await handle_start()

# Обработчики напоминаний
@on_callback("search_info")
async def handle_search_info():
    await write_translated_message("Функция поиска информации в разработке...")
    await button([["Вернуться в главное меню", "back_to_menu"]])

@on_callback("create_notification")
async def handle_create_notification():
    # Инициализируем PostgreSQL
    await init_postgres()
    
    # Запрашиваем текст и время напоминания
    await message_with_buttons("Введите текст напоминания и дату/время в формате:\n[текст] дд.мм.гггг чч:мм\n\nНапример: Помыться 15.06.2023 18:30", [
        [["Отмена", "back_to_menu"]]
    ])

@on_callback("list_notifications")
async def handle_list_notifications():
    try:
        # Инициализируем PostgreSQL
        conn = await init_postgres()
        if not conn:
            await write_translated_message("Ошибка подключения к базе данных. Попробуйте позже.")
            await button([["Вернуться в главное меню", "back_to_menu"]])
            return
            
        # Получаем ID пользователя
        user_id = await get_user_id()
        
        # Получаем список напоминаний напрямую из БД
        try:
            notifications = await conn.fetch('''
                SELECT id, text, date, time 
                FROM notifications 
                WHERE user_id = $1 AND is_sent = false
                ORDER BY date, time
            ''', user_id)
            
            if not notifications or len(notifications) == 0:
                await write_translated_message("У вас нет активных напоминаний.")
                await button([["Вернуться в главное меню", "back_to_menu"]])
                return
            
            # Формируем текст списка напоминаний
            message = "Ваши напоминания:\n\n"
            for i, notification in enumerate(notifications, 1):
                message += f"{i}. {notification['text']} - {notification['date']} в {notification['time']}\n"
            
            await write_translated_message(message)
            
            # Формируем кнопки для удаления напоминаний
            buttons = []
            for i, notification in enumerate(notifications, 1):
                buttons.append([f"❌ Удалить #{i}", f"delete_notification_{notification['id']}"])
            
            buttons.append(["Вернуться в главное меню", "back_to_menu"])
            await button(buttons)
        except Exception as db_error:
            await write_translated_message(f"Ошибка при получении списка напоминаний: {str(db_error)}")
            await button([["Вернуться в главное меню", "back_to_menu"]])
    except Exception as e:
        # Обработка ошибки, показываем сообщение пользователю
        await write_translated_message(f"Произошла ошибка: {str(e)}")
        await button([["Вернуться в главное меню", "back_to_menu"]])

@on_callback("check_notifications")
async def handle_check_notifications():
    # Инициализируем PostgreSQL
    conn = await init_postgres()
    if not conn:
        await write_translated_message("Ошибка подключения к базе данных. Попробуйте позже.")
        await button([["Вернуться в главное меню", "back_to_menu"]])
        return
        
    # Получаем ID пользователя
    user_id = await get_user_id()
    
    # Получаем активные напоминания на текущую дату и время напрямую из БД
    try:
        from datetime import datetime
        
        # Получаем текущую дату и время
        now = datetime.now()
        current_date = now.strftime("%d.%m.%Y")
        current_time = now.strftime("%H:%M")
        
        # Запрашиваем напоминания на текущую дату
        current_notifications = await conn.fetch('''
            SELECT id, text, time 
            FROM notifications 
            WHERE user_id = $1 
            AND date = $2 
            AND is_sent = false
            ORDER BY time
        ''', user_id, current_date)
        
        if current_notifications and len(current_notifications) > 0:
            message = f"У вас {len(current_notifications)} напоминаний на сегодня ({current_date}):\n\n"
            for i, notification in enumerate(current_notifications, 1):
                message += f"{i}. {notification['text']} - {notification['time']}\n"
            await write_translated_message(message)
        else:
            await write_translated_message(f"У вас нет напоминаний на сегодня ({current_date}).")
    except Exception as db_error:
        await write_translated_message(f"Ошибка при получении активных напоминаний: {str(db_error)}")
    
    await button([["Вернуться в главное меню", "back_to_menu"]])

@on_text_message
async def handle_text_message(text):
    # Инициализируем PostgreSQL
    conn = await init_postgres()
    if not conn:
        await write_translated_message("Ошибка подключения к базе данных. Попробуйте позже.")
        await button([["Вернуться в главное меню", "back_to_menu"]])
        return
        
    # Получаем ID пользователя
    user_id = await get_user_id()
    
    # Обработка создания напоминания
    if len(text) < 10:  # Минимальная длина для текста + даты/времени
        await write_translated_message("Текст слишком короткий. Укажите текст напоминания и дату/время в формате:\n[текст] дд.мм.гггг чч:мм")
        return
    
    try:
        # Ищем дату и время в формате дд.мм.гггг чч:мм
        parts = text.split()
        date_time_part = None
        date_part = None
        time_part = None
        text_part = []
        
        # Проходим с конца текста, ищем дату и время
        for i in range(len(parts)-1, -1, -1):
            # Проверяем формат времени чч:мм
            if ":" in parts[i] and len(parts[i]) == 5 and time_part is None:
                time_part = parts[i]
                continue
                
            # Проверяем формат даты дд.мм.гггг
            if "." in parts[i] and len(parts[i]) == 10 and date_part is None:
                date_part = parts[i]
                continue
                
            # Если еще не нашли дату или время, добавляем к тексту
            text_part.insert(0, parts[i])
        
        # Если не нашли дату или время
        if date_part is None or time_part is None:
            await write_translated_message("Не могу распознать дату или время. Укажите их в формате дд.мм.гггг чч:мм в конце сообщения.")
            return
            
        # Собираем текст напоминания
        notification_text = " ".join(text_part)
        
        # Создаем напоминание напрямую в базе данных
        try:
            # Исполняем SQL-запрос напрямую с помощью нашего соединения
            notification_id = await conn.fetchval('''
                INSERT INTO notifications (user_id, text, date, time, is_sent)
                VALUES ($1, $2, $3, $4, false)
                RETURNING id
            ''', user_id, notification_text, date_part, time_part)
            
            if notification_id:
                await write_translated_message(f"Напоминание создано!\n\nТекст: {notification_text}\nДата: {date_part}\nВремя: {time_part}")
            else:
                await write_translated_message("Не удалось создать напоминание. Попробуйте еще раз.")
        except Exception as db_error:
            await write_translated_message(f"Ошибка при сохранении напоминания в базу данных: {str(db_error)}")
    except Exception as e:
        await write_translated_message(f"Ошибка при создании напоминания: {str(e)}\n\nУбедитесь, что вы указали дату и время в формате дд.мм.гггг чч:мм.")
    
    # Возвращаемся в главное меню
    await button([
        ["Создать еще напоминание", "create_notification"],
        ["Мои напоминания", "list_notifications"],
        ["Вернуться в меню", "back_to_menu"]
    ])

# Обработчики callback для удаления напоминаний
@on_callback("delete_notification_")
async def handle_delete_notification(callback_data):
    # Инициализируем PostgreSQL
    conn = await init_postgres()
    if not conn:
        await write_translated_message("Ошибка подключения к базе данных. Попробуйте позже.")
        await button([["Вернуться в главное меню", "back_to_menu"]])
        return
        
    # Получаем ID пользователя
    user_id = await get_user_id()
    
    # Извлекаем id напоминания из callback_data
    notification_id = int(callback_data.replace("delete_notification_", ""))
    
    # Удаляем напоминание напрямую из БД
    try:
        # Удаляем напоминание, убедившись, что оно принадлежит текущему пользователю
        result = await conn.execute('''
            DELETE FROM notifications 
            WHERE id = $1 AND user_id = $2
        ''', notification_id, user_id)
        
        # Проверяем результат операции
        if result and "DELETE" in result:
            await write_translated_message(f"Напоминание #{notification_id} удалено.")
        else:
            await write_translated_message(f"Не удалось удалить напоминание #{notification_id}.")
    except Exception as db_error:
        await write_translated_message(f"Ошибка при удалении напоминания: {str(db_error)}")
        await button([["Вернуться в главное меню", "back_to_menu"]])
        return
    
    # Обновляем список напоминаний
    await handle_list_notifications()

# Запуск бота
if __name__ == "__main__":
    # Не используем asyncio.run, чтобы не создавать конфликтов с event loop телеграм-бота
    run_bot(BOT_TOKEN) 