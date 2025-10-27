import os
import sqlite3

def create_user_documents_table():
    """
    Create the user_documents table if it doesn't exist.
    """
    db_path = os.path.join(os.path.dirname(__file__), '..', 'db', 'users.db')
    
    with sqlite3.connect(db_path) as conn:
        c = conn.cursor()
        
        # Check if the table already exists
        c.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='user_documents'
        """)
        
        if not c.fetchone():
            print("Creating user_documents table...")
            c.execute('''
                CREATE TABLE user_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    description TEXT,
                    uploaded_at TEXT NOT NULL,
                    uploaded_by INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY (uploaded_by) REFERENCES users (id) ON DELETE SET NULL
                )
            ''')
            print("Successfully created user_documents table.")
        else:
            print("user_documents table already exists.")

if __name__ == "__main__":
    create_user_documents_table()
