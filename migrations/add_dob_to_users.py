import os
import sqlite3

def add_dob_to_users():
    """
    Add date_of_birth column to users table if it doesn't exist.
    """
    db_path = os.path.join(os.path.dirname(__file__), '..', 'db', 'users.db')
    
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        
        # Check if the column already exists
        c.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'date_of_birth' not in columns:
            print("Adding date_of_birth column to users table...")
            c.execute('''
                ALTER TABLE users 
                ADD COLUMN date_of_birth TEXT
            ''')
            print("Successfully added date_of_birth column.")
        else:
            print("date_of_birth column already exists in users table.")

if __name__ == "__main__":
    add_dob_to_users()
