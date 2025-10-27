import sqlite3
import os

def check_tables():
    db_path = os.path.join('db', 'users.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get list of all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("Tables in the database:")
    for table in tables:
        print(f"\nTable: {table[0]}")
        try:
            # Get table info
            cursor.execute(f"PRAGMA table_info({table[0]});")
            columns = cursor.fetchall()
            print("Columns:")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
        except sqlite3.Error as e:
            print(f"  Error getting schema: {e}")
    
    conn.close()

if __name__ == "__main__":
    check_tables()
