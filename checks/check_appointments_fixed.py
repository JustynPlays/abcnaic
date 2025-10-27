#!/usr/bin/env python3

import sys
import os
sys.path.append(r'c:\xampp2\htdocs\ABC-PWA hhh fix')

from app import create_app

def check_database():
    """Check database connection and appointments table"""
    # Test database connection and appointments table
    app = create_app()

    with app.app_context():
        # Get the get_db function from the app
        get_db = app.get_db
        conn = get_db()
        c = conn.cursor()

        # Check if appointments table exists and has data
        c.execute("SELECT COUNT(*) FROM appointments")
        count = c.fetchone()[0]
        print(f'Total appointments in database: {count}')

        # Show recent appointments if any exist
        if count > 0:
            c.execute("SELECT id, service, appointment_date, patient_name, status FROM appointments ORDER BY created_at DESC LIMIT 5")
            appointments = c.fetchall()
            print('Recent appointments:')
            for apt in appointments:
                print(f'  - ID: {apt["id"]}, Service: {apt["service"]}, Date: {apt["appointment_date"]}, Patient: {apt["patient_name"]}, Status: {apt["status"]}')
        else:
            print('No appointments found in database')

        conn.close()

if __name__ == "__main__":
    check_database()
