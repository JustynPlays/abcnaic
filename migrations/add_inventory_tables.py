import sqlite3
from datetime import datetime

def migrate(database_path):
    conn = sqlite3.connect(database_path)
    c = conn.cursor()
    
    try:
        # Create inventory_categories table
        c.execute('''
        CREATE TABLE IF NOT EXISTS inventory_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        ''')
        
        # Create inventory_items table
        c.execute('''
        CREATE TABLE IF NOT EXISTS inventory_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            category_id INTEGER,
            quantity INTEGER NOT NULL DEFAULT 0,
            unit TEXT NOT NULL,  # e.g., vials, boxes, pieces
            min_quantity INTEGER DEFAULT 0,
            max_quantity INTEGER,
            location TEXT,
            lot_number TEXT,
            expiration_date TEXT,
            supplier_info TEXT,
            notes TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (category_id) REFERENCES inventory_categories(id)
        )
        ''')
        
        # Create inventory_transactions table
        c.execute('''
        CREATE TABLE IF NOT EXISTS inventory_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            transaction_type TEXT NOT NULL,  # 'in', 'out', 'adjustment', 'expired', etc.
            quantity INTEGER NOT NULL,
            previous_quantity INTEGER NOT NULL,
            new_quantity INTEGER NOT NULL,
            reference_type TEXT,  # e.g., 'vaccine_record', 'manual', 'received', etc.
            reference_id INTEGER,
            notes TEXT,
            created_by INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY (item_id) REFERENCES inventory_items(id)
        )
        ''')
        
        # Create indexes for better performance
        c.execute('CREATE INDEX IF NOT EXISTS idx_inventory_items_category ON inventory_items(category_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_inventory_transactions_item ON inventory_transactions(item_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_inventory_items_expiration ON inventory_items(expiration_date)')
        
        # Insert default categories if they don't exist
        default_categories = [
            ('Vaccines', 'All types of vaccines'),
            ('Medical Supplies', 'Syringes, needles, gloves, etc.'),
            ('Medication', 'General medications and treatments'),
            ('Diagnostic Kits', 'Test kits and diagnostic tools')
        ]
        
        current_time = datetime.now().isoformat()
        for category in default_categories:
            c.execute('''
            INSERT OR IGNORE INTO inventory_categories (name, description, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ''', (*category, current_time, current_time))
        
        conn.commit()
        print("Successfully created inventory tables and default categories.")
        
    except sqlite3.Error as e:
        print(f"Error creating inventory tables: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    import os
    from app import get_db_path
    
    db_path = get_db_path()
    migrate(db_path)
