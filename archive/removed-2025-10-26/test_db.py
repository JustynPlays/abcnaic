#!/usr/bin/env python3

import sys
import os
sys.path.append(r'c:\xampp2\htdocs\ABC-PWA hhh fix')

from app import create_app

def test_database():
    """Test database initialization and table creation"""
    # Test app creation
    app = create_app()
    print('SUCCESS: Flask app created successfully!')

    # Test database initialization
    with app.app_context():
        from app import get_db
        conn = get_db()
        c = conn.cursor()

        # Check if appointments table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='appointments'")
        table_exists = c.fetchone()
        print(f'Appointments table exists: {table_exists is not None}')

        if table_exists:
            # Check table structure
            c.execute('PRAGMA table_info(appointments)')
            columns = c.fetchall()
            print('Appointments table columns:')
            for col in columns:
                print(f'  - {col["name"]}: {col["type"]}')

        conn.close()

    print('Database check completed!')

if __name__ == "__main__":
    test_database()

