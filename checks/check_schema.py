#!/usr/bin/env python3

import sys
import os
sys.path.append(r'c:\xampp2\htdocs\ABC-PWA hhh fix')

from app import create_app

def check_appointments_schema():
    """Check the actual appointments table schema"""
    app = create_app()

    with app.app_context():
        get_db = app.get_db
        conn = get_db()
        c = conn.cursor()

        # Check the actual appointments table schema
        c.execute("PRAGMA table_info(appointments)")
        columns = c.fetchall()
        print('Actual appointments table columns:')
        for col in columns:
            print(f'  - {col["name"]}: {col["type"]} ({"not null" if col["notnull"] else "nullable"})')

        conn.close()

if __name__ == "__main__":
    check_appointments_schema()
