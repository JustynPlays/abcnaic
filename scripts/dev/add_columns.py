#!/usr/bin/env python3

import sys
import os
sys.path.append(r'c:\xampp2\htdocs\ABC-PWA hhh fix')

from app import create_app

def add_missing_columns():
    """Add missing columns to appointments table"""
    app = create_app()

    with app.app_context():
        get_db = app.get_db
        conn = get_db()
        c = conn.cursor()

        # Check if these columns exist
        columns_to_check = ['animal_type', 'exposure_type', 'bite_location', 'category']

        print('Checking for missing columns:')
        for col in columns_to_check:
            c.execute("SELECT COUNT(*) FROM pragma_table_info('appointments') WHERE name=?", (col,))
            exists = c.fetchone()[0] > 0
            print(f'  - {col}: {"EXISTS" if exists else "MISSING"}')

            if not exists:
                print(f'    Adding column: {col}')
                c.execute(f'ALTER TABLE appointments ADD COLUMN {col} TEXT')

        conn.commit()
        print('Columns added successfully!')

        # Verify the updated schema
        c.execute("PRAGMA table_info(appointments)")
        columns = c.fetchall()
        print('Updated appointments table columns:')
        for col in columns:
            print(f'  - {col["name"]}: {col["type"]}')

        conn.close()

if __name__ == "__main__":
    add_missing_columns()
