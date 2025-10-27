import os
import sqlite3

def apply_migration():
    # Get the path to the database
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'users.db')
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # Check if the table already exists
        c.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='user_documents'
        """)
        
        if c.fetchone() is None:
            # Create the user_documents table
            c.execute('''
                CREATE TABLE user_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    filename TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER,
                    description TEXT,
                    uploaded_at TEXT NOT NULL,
                    uploaded_by INTEGER,
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                    FOREIGN KEY (uploaded_by) REFERENCES users (id) ON DELETE SET NULL
                )
            ''')
            
            # Create an index on user_id for faster lookups
            c.execute('''
                CREATE INDEX idx_user_documents_user_id 
                ON user_documents (user_id)
            ''')
            
            conn.commit()
            print("Successfully created user_documents table and index.")
        else:
            print("user_documents table already exists. No changes made.")
            
    except Exception as e:
        conn.rollback()
        print(f"Error applying migration: {str(e)}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    apply_migration()
