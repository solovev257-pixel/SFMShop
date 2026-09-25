from src.database.connection import get_connection

def run_migrations():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                ALTER TABLE orders 
                ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'pending'
            """)
            print("Миграции выполнены успешно")

if __name__ == "__main__":
    run_migrations()