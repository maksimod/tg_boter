import asyncio
import asyncpg
import sys
import os
from datetime import datetime
from tabulate import tabulate

# Настройки БД
BOT_PREFIX = "tgbot_"

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

# Создаем пользовательское меню для проверки
async def show_menu():
    """Показывает меню для проверки различных таблиц"""
    while True:
        print("\n=== МЕНЮ ПРОВЕРКИ БД ===")
        print("1. Проверить все таблицы")
        print("2. Изменить префикс таблиц")
        print("0. Выход")
        
        choice = input("\nВыберите опцию: ")
        
        if choice == "1":
            await check_tables()
        elif choice == "2":
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