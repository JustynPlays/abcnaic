#!/usr/bin/env python3

import sys
import os
sys.path.append(r'c:\xampp2\htdocs\ABC-PWA hhh fix')

from app import create_app

def test_appointment_insertion():
    """Test manual appointment insertion to debug the issue"""
    app = create_app()

    with app.app_context():
        # Get the get_db function from the app
        get_db = app.get_db
        conn = get_db()
        c = conn.cursor()

        # Test data that should match the expected session structure
        test_appointment = {
            'service': 'Anti-Rabies Vaccine',
            'date': '2025-01-15',
            'time': '10:00',
            'name': 'Test Patient',
            'address': 'Test Address',
            'age': '25',
            'gender': 'male',
            'phone': '9123456789',
            'branch': 'Main Branch',
            'email': 'test@example.com',
            'price': '425.00',
            'animal_type': 'dog',
            'exposure_type': 'bite',
            'bite_location': 'arm,hand',
            'category': '1'
        }

        # Test user_id (this would normally come from session)
        test_user_id = 1

        print("Testing appointment insertion...")
        print(f"Test data: {test_appointment}")

        try:
            # Try the exact same insertion as in appointment_summary route
            c.execute('''
                INSERT INTO appointments (
                    user_id, service, appointment_date, appointment_time,
                    patient_name, patient_address, patient_age, patient_gender,
                    patient_phone, branch, patient_email, price, animal_type,
                    exposure_type, bite_location, category
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                test_user_id,
                test_appointment.get('service', 'Rabies Vaccination'),
                test_appointment.get('date'),
                test_appointment.get('time'),
                test_appointment.get('name'),
                test_appointment.get('address'),
                int(test_appointment.get('age', 0)) if test_appointment.get('age') else None,
                test_appointment.get('gender'),
                test_appointment.get('phone'),
                test_appointment.get('branch'),
                test_appointment.get('email'),
                float(test_appointment.get('price', 0).replace('₱', '').replace(',', '')) if test_appointment.get('price') else 0.0,
                test_appointment.get('animal_type'),
                test_appointment.get('exposure_type'),
                test_appointment.get('bite_location', ''),
                test_appointment.get('category')
            ))

            conn.commit()
            print("SUCCESS: Appointment inserted successfully!")

            # Verify the insertion
            c.execute('SELECT COUNT(*) FROM appointments WHERE user_id = ?', (test_user_id,))
            count = c.fetchone()[0]
            print(f"Appointments for user {test_user_id}: {count}")

            if count > 0:
                c.execute('SELECT id, service, appointment_date, patient_name FROM appointments WHERE user_id = ? ORDER BY id DESC LIMIT 1', (test_user_id,))
                apt = c.fetchone()
                print(f"Latest appointment: ID={apt['id']}, Service={apt['service']}, Date={apt['appointment_date']}, Patient={apt['patient_name']}")

        except Exception as e:
            print(f"ERROR inserting appointment: {str(e)}")
            print(f"Error type: {type(e)}")

            # Check if it's a foreign key constraint error (user doesn't exist)
            if 'FOREIGN KEY' in str(e):
                print("This might be a foreign key constraint error - the user_id might not exist")

                # Check if user exists
                c.execute('SELECT COUNT(*) FROM users WHERE id = ?', (test_user_id,))
                user_count = c.fetchone()[0]
                print(f"User {test_user_id} exists: {user_count > 0}")

        finally:
            # Clean up the test data
            try:
                c.execute('DELETE FROM appointments WHERE user_id = ? AND patient_name = ?', (test_user_id, 'Test Patient'))
                conn.commit()
                print("Test appointment cleaned up")
            except:
                pass

            conn.close()

if __name__ == "__main__":
    test_appointment_insertion()
