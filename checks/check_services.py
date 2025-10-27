#!/usr/bin/env python3

import sys
import os
sys.path.append(r'c:\xampp2\htdocs\ABC-PWA hhh fix')

from app import create_app

def check_services():
    """Check services table and data"""
    app = create_app()

    with app.app_context():
        get_db = app.get_db
        conn = get_db()
        c = conn.cursor()

        # Check if services table exists
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='services'")
        table_exists = c.fetchone()
        print(f'Services table exists: {table_exists is not None}')

        if table_exists:
            # Check table structure
            c.execute("PRAGMA table_info(services)")
            columns = c.fetchall()
            print('Services table columns:')
            for col in columns:
                print(f'  - {col["name"]}: {col["type"]} ({"not null" if col["notnull"] else "nullable"})')

            # Check if there are any services
            c.execute("SELECT COUNT(*) FROM services WHERE is_active = 1")
            count = c.fetchone()[0]
            print(f'Active services count: {count}')

            if count > 0:
                c.execute("SELECT name, category, price, duration_minutes FROM services WHERE is_active = 1 ORDER BY category, name")
                services = c.fetchall()
                print('Active services:')
                for service in services:
                    print(f'  - {service["name"]} ({service["category"]}): ₱{service["price"]} - {service["duration_minutes"]} mins')
            else:
                print('No active services found')
        else:
            print('Services table does not exist')

        conn.close()

if __name__ == "__main__":
    check_services()
