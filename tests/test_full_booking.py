#!/usr/bin/env python3

import sys
import os
sys.path.append(r'c:\xampp2\htdocs\ABC-PWA hhh fix')

from app import create_app
from werkzeug.security import generate_password_hash

def test_full_booking_flow():
    """Test the complete booking flow with user creation"""
    app = create_app()

    with app.app_context():
        get_db = app.get_db
        conn = get_db()
        c = conn.cursor()

        # Create a test user first
        test_email = "test_booking@example.com"
        test_name = "Test Booking User"
        test_username = "testbooking"

        try:
            # Check if user already exists
            c.execute("SELECT id FROM users WHERE email = ?", (test_email,))
            existing_user = c.fetchone()

            if existing_user:
                test_user_id = existing_user[0]
                print(f"Using existing user ID: {test_user_id}")
            else:
                # Create new test user
                password_hash = generate_password_hash("testpassword123")
                c.execute("""
                    INSERT INTO users (name, username, email, password_hash, is_verified, created_at)
                    VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                """, (test_name, test_username, test_email, password_hash))
                test_user_id = c.lastrowid
                print(f"Created new user ID: {test_user_id}")

            conn.commit()

            # Now test appointment insertion with the real user_id
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

            print(f"Testing appointment insertion for user {test_user_id}...")

            # Insert appointment
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
            c.execute("SELECT COUNT(*) FROM appointments WHERE user_id = ?", (test_user_id,))
            count = c.fetchone()[0]
            print(f"Appointments for user {test_user_id}: {count}")

            if count > 0:
                c.execute("SELECT id, service, appointment_date, patient_name FROM appointments WHERE user_id = ? ORDER BY id DESC LIMIT 1", (test_user_id,))
                apt = c.fetchone()
                print(f"Latest appointment: ID={apt['id']}, Service={apt['service']}, Date={apt['appointment_date']}, Patient={apt['patient_name']}")

                # Test if this appointment shows up in admin queries
                print("\nTesting admin queries:")

                # Test the admin_users query (which gets appointment data for users)
                c.execute("""
                    SELECT appointment_date, appointment_time, service
                    FROM appointments
                    WHERE user_id = ?
                    ORDER BY appointment_date DESC, appointment_time DESC
                    LIMIT 1
                """, (test_user_id,))
                appointment = c.fetchone()

                if appointment:
                    recent_appointment = f"{appointment['appointment_date']} | {appointment['appointment_time']}"
                    print(f"Recent appointment for admin view: {recent_appointment}")

                # Test appointment count
                c.execute("SELECT COUNT(*) FROM appointments WHERE user_id = ?", (test_user_id,))
                count_result = c.fetchone()
                appointment_count = count_result[0] if count_result else 0
                print(f"Appointment count for admin view: {appointment_count}")

                # Test the my_bookings query
                c.execute("SELECT id, service, appointment_date, status FROM appointments WHERE user_id = ?", (test_user_id,))
                bookings = c.fetchall()
                print(f"Bookings for my_bookings view: {len(bookings)} found")

                for booking in bookings:
                    print(f"  - Booking ID: {booking['id']}, Service: {booking['service']}, Date: {booking['appointment_date']}")

        except Exception as e:
            print(f"ERROR: {str(e)}")
            print(f"Error type: {type(e)}")

            # Check if it's a foreign key constraint error
            if 'FOREIGN KEY' in str(e):
                print("This is a foreign key constraint error - the user_id might not exist")
                c.execute("SELECT COUNT(*) FROM users WHERE id = ?", (test_user_id,))
                user_count = c.fetchone()[0]
                print(f"User {test_user_id} exists: {user_count > 0}")

        finally:
            # Clean up test data (but keep one appointment for testing)
            try:
                # Only delete if there are multiple appointments
                c.execute("SELECT COUNT(*) FROM appointments WHERE user_id = ?", (test_user_id,))
                count = c.fetchone()[0]
                if count > 1:
                    c.execute("DELETE FROM appointments WHERE user_id = ? AND patient_name = ?", (test_user_id, 'Test Patient'))
                    conn.commit()
                    print("Extra test appointments cleaned up")
            except:
                pass

            conn.close()

if __name__ == "__main__":
    test_full_booking_flow()
