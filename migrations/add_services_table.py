import sqlite3
from datetime import datetime

def migrate(database_path):
    conn = sqlite3.connect(database_path)
    c = conn.cursor()

    try:
        # Create services table
        c.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            price REAL NOT NULL DEFAULT 0,
            duration_minutes INTEGER, -- Duration in minutes
            is_active INTEGER DEFAULT 1, -- 1 for active, 0 for inactive
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        ''')

        # Create indexes for better performance
        c.execute('CREATE INDEX IF NOT EXISTS idx_services_name ON services(name)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_services_category ON services(category)')

        # Insert some default services if the table is empty
        c.execute('SELECT COUNT(*) FROM services')
        if c.fetchone()[0] == 0:
            default_services = [
                ('Anti-Rabies Vaccine (Day 0)', 'First dose of anti-rabies vaccine series.', 'Vaccination', 800.00, 15, 1),
                ('Tetanus Toxoid', 'Tetanus toxoid vaccine.', 'Vaccination', 500.00, 15, 1),
                ('Wound Cleaning', 'Standard cleaning and dressing of bite wounds.', 'Consultation', 300.00, 20, 1),
                ('Follow-up Consultation', 'Follow-up check-up for existing patients.', 'Consultation', 250.00, 10, 1)
            ]
            current_time = datetime.now().isoformat()
            for service in default_services:
                c.execute('''
                INSERT INTO services (name, description, category, price, duration_minutes, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (*service, current_time, current_time))

        conn.commit()
        print("Successfully created services table and default services.")

    except sqlite3.Error as e:
        print(f"Error creating services table: {str(e)}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    import os
    # This assumes the script is run from the project root directory.
    db_path = os.path.join('db', 'users.db')
    if not os.path.exists(os.path.dirname(db_path)):
        os.makedirs(os.path.dirname(db_path))
    migrate(db_path)
