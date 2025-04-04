"""
Simple script to check the structure of the notifications table
"""
import psycopg2
from credentials.postgres.config import HOST, PORT, DATABASE, USER, PASSWORD, BOT_PREFIX

def check_table_structure():
    try:
        # Connect to the database
        print(f"Connecting to PostgreSQL: {HOST}:{PORT}, DB: {DATABASE}, User: {USER}")
        conn = psycopg2.connect(
            host=HOST,
            port=PORT,
            database=DATABASE,
            user=USER,
            password=PASSWORD
        )
        
        # Create a cursor
        with conn.cursor() as cursor:
            # Check if notifications table exists
            notifications_table = f"{BOT_PREFIX}notifications"
            cursor.execute(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = '{notifications_table}'
                )
            """)
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                print(f"Table {notifications_table} does not exist!")
                return
            
            # Get column information for the notifications table
            print(f"\nStructure of table {notifications_table}:")
            cursor.execute(f"""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = '{notifications_table}'
                ORDER BY ordinal_position
            """)
            
            columns = cursor.fetchall()
            for column in columns:
                column_name, data_type, is_nullable = column
                print(f"- {column_name}: {data_type} (Nullable: {is_nullable})")
            
            # Get a sample row if available
            print(f"\nSample data from {notifications_table}:")
            cursor.execute(f"SELECT * FROM {notifications_table} LIMIT 1")
            sample = cursor.fetchone()
            if sample:
                cursor.execute(f"""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = '{notifications_table}'
                    ORDER BY ordinal_position
                """)
                column_names = [col[0] for col in cursor.fetchall()]
                print(f"Columns: {', '.join(column_names)}")
                print(f"Sample row: {sample}")
            else:
                print("No data in the table")
    
    except Exception as e:
        print(f"Error checking database: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_table_structure() 