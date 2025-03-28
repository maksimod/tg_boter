import asyncio
import asyncpg

async def check_database():
    try:
        # Подключаемся к базе данных
        conn = await asyncpg.connect(
            host='217.12.37.175',
            port=5433,
            user='python_telebot_test',
            password='ea729&*SyPass',
            database='python_telebot_test'
        )
        
        # Проверяем существование таблицы
        table_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'translations')"
        )
        
        if not table_exists:
            print("Таблица 'translations' не существует в базе данных!")
            await conn.close()
            return
        
        # Получаем количество записей
        count = await conn.fetchval("SELECT COUNT(*) FROM translations")
        print(f"В таблице 'translations' содержится {count} записей.")
        
        # Если есть записи, показываем несколько для примера
        if count > 0:
            rows = await conn.fetch("SELECT source_text, translated_text, source_language, target_language, created_at FROM translations LIMIT 5")
            print("\nПримеры переводов из базы данных:")
            for row in rows:
                src_text = row['source_text'][:30] + "..." if len(row['source_text']) > 30 else row['source_text']
                trans_text = row['translated_text'][:30] + "..." if len(row['translated_text']) > 30 else row['translated_text']
                print(f"- {src_text} → {trans_text} ({row['source_language']} → {row['target_language']}), создан: {row['created_at']}")
        
        # Статистика по языкам
        lang_stats = await conn.fetch("SELECT target_language, COUNT(*) FROM translations GROUP BY target_language ORDER BY COUNT(*) DESC")
        print("\nСтатистика по языкам:")
        for stat in lang_stats:
            print(f"- {stat['target_language']}: {stat['count']} переводов")
        
        await conn.close()
        
    except Exception as e:
        print(f"Ошибка при проверке базы данных: {str(e)}")

if __name__ == "__main__":
    asyncio.run(check_database()) 