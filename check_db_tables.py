import asyncio
import asyncpg
import sys
import os
from datetime import datetime
from tabulate import tabulate

# Настройки БД
BOT_PREFIX = "tgbot_"

# Класс для проверки и создания таблиц
class DbChecker:
    def __init__(self, host, database, user, password, port, table_prefix):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.port = port
        self.table_prefix = table_prefix
        self.conn = None
    
    async def connect(self):
        """Устанавливает соединение с базой данных"""
        try:
            self.conn = await asyncpg.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database
            )
            return True
        except Exception as e:
            print(f"Ошибка при подключении к БД: {e}")
            return False
    
    async def close(self):
        """Закрывает соединение с базой данных"""
        if self.conn:
            await self.conn.close()
    
    async def check_table_exists(self, table_name):
        """Проверяет существует ли таблица в БД"""
        if not self.conn:
            return False
        
        query = """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = $1 AND table_schema = 'public'
        )
        """
        return await self.conn.fetchval(query, table_name)
    
    async def check_users_table(self):
        """Проверяет и создает таблицу пользователей"""
        table_name = f"{self.table_prefix}users"
        result = await self.check_table_exists(table_name)
        
        if not result:
            print(f"Таблица {table_name} не найдена. Создаем...")
            
            create_query = f"""
            CREATE TABLE {table_name} (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id)
            )
            """
            
            try:
                await self.conn.execute(create_query)
                print(f"Таблица {table_name} успешно создана")
            except Exception as e:
                print(f"Ошибка при создании таблицы {table_name}: {e}")
        else:
            print(f"Таблица {table_name} уже существует")
    
    async def check_messages_table(self):
        """Проверяет и создает таблицу для сообщений пользователей"""
        table_name = f"{self.table_prefix}messages"
        result = await self.check_table_exists(table_name)
        
        if not result:
            print(f"Таблица {table_name} не найдена. Создаем...")
            
            create_query = f"""
            CREATE TABLE {table_name} (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                message_text TEXT NOT NULL,
                is_bot_message BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            );
            """
            
            try:
                await self.conn.execute(create_query)
                print(f"Таблица {table_name} успешно создана")
            except Exception as e:
                print(f"Ошибка при создании таблицы {table_name}: {e}")
        else:
            print(f"Таблица {table_name} уже существует")
    
    async def check_bots_table(self):
        """Проверяет и создает таблицу ботов"""
        table_name = f"{self.table_prefix}bots"
        result = await self.check_table_exists(table_name)
        
        if not result:
            print(f"Таблица {table_name} не найдена. Создаем...")
            
            create_query = f"""
            CREATE TABLE {table_name} (
                id SERIAL PRIMARY KEY,
                bot_id TEXT NOT NULL,
                bot_name TEXT NOT NULL,
                bot_token TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(bot_id)
            );
            """
            
            try:
                await self.conn.execute(create_query)
                print(f"Таблица {table_name} успешно создана")
            except Exception as e:
                print(f"Ошибка при создании таблицы {table_name}: {e}")
        else:
            print(f"Таблица {table_name} уже существует")
    
    async def check_bot_user_settings_table(self):
        """Проверяет и создает таблицу настроек пользователя бота"""
        table_name = f"{self.table_prefix}bot_user_settings"
        result = await self.check_table_exists(table_name)
        
        if not result:
            print(f"Таблица {table_name} не найдена. Создаем...")
            
            create_query = f"""
            CREATE TABLE {table_name} (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                bot_id INTEGER NOT NULL,
                language TEXT DEFAULT 'ru',
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(user_id, bot_id)
            );
            """
            
            try:
                await self.conn.execute(create_query)
                print(f"Таблица {table_name} успешно создана")
            except Exception as e:
                print(f"Ошибка при создании таблицы {table_name}: {e}")
        else:
            print(f"Таблица {table_name} уже существует")
    
    async def check_bot_user_state_table(self):
        """Проверяет и создает таблицу состояний пользователя"""
        table_name = f"{self.table_prefix}bot_user_state"
        result = await self.check_table_exists(table_name)
        
        if not result:
            print(f"Таблица {table_name} не найдена. Создаем...")
            
            create_query = f"""
            CREATE TABLE {table_name} (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                bot_id INTEGER NOT NULL,
                state_name TEXT,
                state_data JSONB,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(user_id, bot_id)
            );
            """
            
            try:
                await self.conn.execute(create_query)
                print(f"Таблица {table_name} успешно создана")
            except Exception as e:
                print(f"Ошибка при создании таблицы {table_name}: {e}")
        else:
            print(f"Таблица {table_name} уже существует")
    
    async def check_translations_table(self):
        """Проверяет и создает таблицу переводов"""
        table_name = f"{self.table_prefix}translations"
        result = await self.check_table_exists(table_name)
        
        if not result:
            print(f"Таблица {table_name} не найдена. Создаем...")
            
            create_query = f"""
            CREATE TABLE {table_name} (
                id SERIAL PRIMARY KEY,
                source_text TEXT NOT NULL,
                translated_text TEXT NOT NULL,
                source_language VARCHAR(50) NOT NULL,
                target_language VARCHAR(50) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_text, target_language)
            );
            """
            
            try:
                await self.conn.execute(create_query)
                print(f"Таблица {table_name} успешно создана")
            except Exception as e:
                print(f"Ошибка при создании таблицы {table_name}: {e}")
        else:
            print(f"Таблица {table_name} уже существует")
    
    async def check_all_tables(self):
        """Проверяет и создает все необходимые таблицы"""
        await self.check_users_table()
        await self.check_bots_table()
        await self.check_bot_user_settings_table()
        await self.check_bot_user_state_table()
        await self.check_translations_table()
        await self.check_messages_table()

# Загрузка настроек PostgreSQL
def load_postgres_config():
    """Загружает настройки подключения к PostgreSQL из файла конфигурации"""
    global BOT_PREFIX
    
    try:
        # Проверяем наличие папки credentials/postgres
        if os.path.exists("credentials/postgres"):
            try:
                from credentials.postgres.config import (
                    HOST, DATABASE, USER, PASSWORD, PORT, BOT_PREFIX as PREFIX
                )
                BOT_PREFIX = PREFIX if PREFIX else BOT_PREFIX
                print(f"Настройки PostgreSQL загружены из config.py. BOT_PREFIX: {BOT_PREFIX}")
                return HOST, DATABASE, USER, PASSWORD, PORT
            except ImportError:
                print("Не удалось загрузить настройки PostgreSQL из модуля")
            except Exception as e:
                print(f"Ошибка при загрузке настроек PostgreSQL: {e}")
                
    except Exception as e:
        print(f"Ошибка при загрузке настроек PostgreSQL: {e}")
    
    print("Используем настройки PostgreSQL по умолчанию")
    return "localhost", "telegram_bot", "postgres", "postgres", 5432

async def check_tables():
    """Проверяет существование таблиц в БД и выводит их содержимое"""
    try:
        # Загружаем настройки PostgreSQL
        host, database, user, password, port = load_postgres_config()
        
        print(f"Подключение к PostgreSQL: {host}:{port}, DB: {database}, User: {user}")
        
        # Подключаемся к базе данных
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        
        print(f"Соединение с PostgreSQL успешно установлено")
        
        # Получаем список всех таблиц в базе данных
        all_tables = await conn.fetch(
            """
            SELECT tablename FROM pg_tables 
            WHERE schemaname='public'
            ORDER BY tablename
            """
        )
        
        # Фильтруем только таблицы с нашим префиксом
        bot_tables = [table['tablename'] for table in all_tables if table['tablename'].startswith(BOT_PREFIX)]
        
        if not bot_tables:
            print(f"Таблицы с префиксом '{BOT_PREFIX}' не найдены в базе данных {database}")
            return
        
        print(f"\nНайдены следующие таблицы с префиксом '{BOT_PREFIX}':")
        for i, table in enumerate(bot_tables, 1):
            print(f"{i}. {table}")
        
        # Проверяем наличие ожидаемых таблиц
        expected_tables = [f"{BOT_PREFIX}users", f"{BOT_PREFIX}messages", f"{BOT_PREFIX}translations"]
        missing_tables = [table for table in expected_tables if table not in bot_tables]
        
        if missing_tables:
            print(f"\nВНИМАНИЕ: Не найдены следующие таблицы:")
            for table in missing_tables:
                print(f"- {table}")
        else:
            print(f"\nВсе необходимые таблицы найдены!")
        
        # Анализируем содержимое каждой таблицы
        for table_name in bot_tables:
            # Получаем структуру таблицы
            table_structure = await conn.fetch(
                f"""
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns
                WHERE table_name = $1
                ORDER BY ordinal_position
                """,
                table_name
            )
            
            print(f"\n\n=== Структура таблицы {table_name} ===")
            structure_data = []
            for column in table_structure:
                data_type = column['data_type']
                if column['character_maximum_length']:
                    data_type += f"({column['character_maximum_length']})"
                structure_data.append([column['column_name'], data_type])
            
            print(tabulate(structure_data, headers=["Колонка", "Тип данных"], tablefmt="grid"))
            
            # Получаем количество записей
            count = await conn.fetchval(f"SELECT COUNT(*) FROM {table_name}")
            print(f"\nВсего записей: {count}")
            
            # Получаем записи, но не больше 20
            if count > 0:
                # Получаем все колонки
                columns = [col['column_name'] for col in table_structure]
                columns_str = ', '.join(columns)
                
                records = await conn.fetch(f"SELECT {columns_str} FROM {table_name} LIMIT 20")
                
                print("\nПервые 20 записей:")
                
                # Преобразуем записи в список списков для tabulate
                rows = []
                for record in records:
                    row = []
                    for column in columns:
                        value = record[column]
                        
                        # Форматируем дату/время для лучшей читаемости
                        if isinstance(value, datetime):
                            value = value.strftime('%Y-%m-%d %H:%M:%S')
                        
                        # Обрезаем длинные текстовые значения
                        if isinstance(value, str) and len(value) > 50:
                            value = value[:47] + "..."
                            
                        row.append(value)
                    rows.append(row)
                
                print(tabulate(rows, headers=columns, tablefmt="grid"))
            else:
                print("Таблица пуста")
        
        # Закрываем соединение
        await conn.close()
        
    except Exception as e:
        print(f"Ошибка при проверке таблиц: {e}")
        return

async def create_tables():
    """Создает все необходимые таблицы в базе данных"""
    try:
        # Загружаем настройки PostgreSQL
        host, database, user, password, port = load_postgres_config()
        
        print(f"Подключение к PostgreSQL для создания таблиц: {host}:{port}, DB: {database}, User: {user}")
        
        # Создаем объект для проверки и создания таблиц
        db_checker = DbChecker(host, database, user, password, port, BOT_PREFIX)
        
        # Устанавливаем соединение
        if not await db_checker.connect():
            print("Не удалось подключиться к базе данных")
            return
        
        print("Соединение с PostgreSQL успешно установлено")
        
        # Проверяем и создаем все таблицы
        await db_checker.check_all_tables()
        
        # Закрываем соединение
        await db_checker.close()
        
        print("Все таблицы проверены и созданы")
        
    except Exception as e:
        print(f"Ошибка при создании таблиц: {e}")
        return

# Создаем пользовательское меню для проверки
async def show_menu():
    """Показывает меню для проверки различных таблиц"""
    while True:
        print("\n=== МЕНЮ ПРОВЕРКИ БД ===")
        print("1. Проверить все таблицы")
        print("2. Создать недостающие таблицы")
        print("3. Изменить префикс таблиц")
        print("0. Выход")
        
        choice = input("\nВыберите опцию: ")
        
        if choice == "1":
            await check_tables()
        elif choice == "2":
            await create_tables()
        elif choice == "3":
            global BOT_PREFIX
            new_prefix = input(f"Введите новый префикс (текущий: {BOT_PREFIX}): ")
            if new_prefix:
                BOT_PREFIX = new_prefix
                print(f"Префикс изменен на: {BOT_PREFIX}")
        elif choice == "0":
            print("Выход из программы")
            break
        else:
            print("Неверный выбор. Попробуйте снова.")
        
        if choice != "0":
            input("\nНажмите Enter для продолжения...")

# Запускаем меню, если скрипт запущен напрямую
if __name__ == "__main__":
    try:
        # Попытка установить tabulate, если не установлен
        try:
            import tabulate
        except ImportError:
            print("Установка пакета tabulate...")
            os.system("pip install tabulate")
            try:
                import tabulate
                print("Пакет tabulate успешно установлен")
            except ImportError:
                print("Не удалось установить tabulate. Установите его вручную: pip install tabulate")
                sys.exit(1)
        
        # Запускаем меню
        asyncio.run(show_menu())
    except KeyboardInterrupt:
        print("\nПрограмма прервана пользователем")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        input("Нажмите Enter для выхода...") 