import os
import sqlite3

def apply_migration():
    # Get the path to the database
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'users.db')
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # Check if the file_size column exists
        c.execute("PRAGMA table_info(user_documents)")
        columns = [column[1] for column in c.fetchall()]
        
        if 'file_size' not in columns:
            # Add the file_size column
            c.execute('''
                ALTER TABLE user_documents
                ADD COLUMN file_size INTEGER
            ''')
            
            conn.commit()
            print("Successfully added file_size column to user_documents table.")
        else:
            print("file_size column already exists in user_documents table.")
            
    except Exception as e:
        conn.rollback()
        print(f"Error applying migration: {str(e)}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    apply_migration()
