#!/usr/bin/env python3

import sys
import os
sys.path.append(r'c:\xampp2\htdocs\ABC-PWA hhh fix')

from app import create_app

def check_all_appointments():
    """Check all appointments in the database"""
    app = create_app()

    with app.app_context():
        get_db = app.get_db
        conn = get_db()
        c = conn.cursor()

        # Check all appointments in the database
        c.execute("SELECT COUNT(*) FROM appointments")
        total_count = c.fetchone()[0]
        print(f'Total appointments in database: {total_count}')

        if total_count > 0:
            # Show all appointments
            c.execute("SELECT * FROM appointments ORDER BY created_at DESC")
            appointments = c.fetchall()
            print('All appointments:')
            for apt in appointments:
                print(f'  - ID: {apt["id"]}, User: {apt["user_id"]}, Service: {apt["service"]}, Date: {apt["appointment_date"]}, Patient: {apt["patient_name"]}')
        else:
            print('No appointments found in database')

        conn.close()

if __name__ == "__main__":
    check_all_appointments()
