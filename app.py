import os
import sqlite3
from datetime import datetime
from flask import Flask
from flask_mail import Mail
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from routes import init_routes
from routes_user_documents import init_document_routes
from routes_inventory import init_inventory_routes
from routes_services import init_services_routes
from routes_appointments import init_appointments_routes
from routes_calendar import init_calendar_routes
from utils.sms_service import SMSService, send_appointment_reminder, send_appointment_confirmation, send_verification_code

def create_app():
    app = Flask(__name__)
    app.secret_key = os.urandom(24)
    # Database setup
    DATABASE_URL = os.environ.get('DATABASE_URL')
    if DATABASE_URL:
        # Use PostgreSQL via psycopg2 when DATABASE_URL is provided.
        # We return a small wrapper with a cursor() method that yields RealDictCursor so existing code
        # that expects dict-like rows (sqlite3.Row) continues to work.
        try:
            import psycopg2
            import psycopg2.extras
        except Exception:
            raise RuntimeError('psycopg2 is required when DATABASE_URL is set. Please install psycopg2-binary')

        class PGConn:
            def __init__(self, dsn):
                # ensure SSL mode if included in URL; leave to psycopg2 to parse
                self._dsn = dsn
                self._conn = None

            def _ensure(self):
                if self._conn is None:
                    self._conn = psycopg2.connect(self._dsn)
                    # Default to autocommit to more closely match sqlite's simple usage pattern
                    # and avoid "current transaction is aborted" states persisting across
                    # multiple cursor calls when exception handling is not exhaustive.
                    try:
                        self._conn.autocommit = True
                    except Exception:
                        pass

            def cursor(self):
                self._ensure()
                real_cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

                # Wrap the real cursor so that code written for sqlite (using '?' placeholders)
                # continues to work with psycopg2 which expects '%s' placeholders.
                class CursorWrapper:
                    def __init__(self, cur):
                        self._cur = cur

                    def execute(self, query, params=None):
                        try:
                            if params is None:
                                return self._cur.execute(query)
                            # Simple placeholder translation: replace SQLite '?' with psycopg2 '%s'
                            q = query.replace('?', '%s')
                            return self._cur.execute(q, params)
                        except Exception:
                            # Ensure the transaction is rolled back to avoid "current transaction is aborted"
                            try:
                                # psycopg2 cursor has a .connection attribute
                                if hasattr(self._cur, 'connection') and self._cur.connection is not None:
                                    self._cur.connection.rollback()
                            except Exception:
                                pass
                            raise

                    def executemany(self, query, seq_of_params):
                        try:
                            q = query.replace('?', '%s')
                            return self._cur.executemany(q, seq_of_params)
                        except Exception:
                            try:
                                if hasattr(self._cur, 'connection') and self._cur.connection is not None:
                                    self._cur.connection.rollback()
                            except Exception:
                                pass
                            raise

                    def fetchone(self):
                        row = self._cur.fetchone()
                        if row is None:
                            return None
                        # If psycopg2 RealDictCursor returns a dict-like row, wrap it so
                        # code that expects sqlite3.Row-style access by integer index
                        # (e.g. row[0]) or by column name (row['col']) continues to work.
                        if isinstance(row, dict):
                            col_names = [d[0] for d in (self._cur.description or [])]

                            class RowWrapper:
                                def __init__(self, data, cols):
                                    self._data = data
                                    self._cols = cols
                                    # Prepare values in column order for index access
                                    self._values = [self._data.get(c) for c in self._cols]

                                def __getitem__(self, key):
                                    if isinstance(key, int):
                                        return self._values[key]
                                    return self._data.get(key)

                                def get(self, key, default=None):
                                    return self._data.get(key, default)

                                def keys(self):
                                    return list(self._data.keys())

                                def items(self):
                                    return self._data.items()

                                def as_dict(self):
                                    return dict(self._data)

                                def __repr__(self):
                                    return f"RowWrapper({self._data})"

                            return RowWrapper(row, col_names)

                        return row

                    def fetchall(self):
                        rows = self._cur.fetchall()
                        if not rows:
                            return rows
                        # If rows are dict-like, wrap each one similarly to fetchone
                        if isinstance(rows[0], dict):
                            col_names = [d[0] for d in (self._cur.description or [])]

                            class RowWrapper:
                                def __init__(self, data, cols):
                                    self._data = data
                                    self._cols = cols
                                    self._values = [self._data.get(c) for c in self._cols]

                                def __getitem__(self, key):
                                    if isinstance(key, int):
                                        return self._values[key]
                                    return self._data.get(key)

                                def get(self, key, default=None):
                                    return self._data.get(key, default)

                                def keys(self):
                                    return list(self._data.keys())

                                def items(self):
                                    return self._data.items()

                                def as_dict(self):
                                    return dict(self._data)

                                def __repr__(self):
                                    return f"RowWrapper({self._data})"

                            return [RowWrapper(r, col_names) for r in rows]

                        return rows

                    def __getattr__(self, name):
                        # Delegate attribute access to the real cursor for others like close()
                        return getattr(self._cur, name)

                return CursorWrapper(real_cur)

            def commit(self):
                if self._conn:
                    return self._conn.commit()

            def rollback(self):
                if self._conn:
                    return self._conn.rollback()

            def close(self):
                if self._conn:
                    try:
                        self._conn.close()
                    finally:
                        self._conn = None

        def get_db():
            # Return a lightweight connection-like wrapper.
            return PGConn(DATABASE_URL)

    else:
        DB_PATH = os.path.join(os.path.dirname(__file__), 'db', 'users.db')
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

        def get_db():
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            return conn

    # Mail setup
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'your_email@gmail.com'  # Replace with your Gmail
    app.config['MAIL_PASSWORD'] = 'your_app_password'     # Replace with App Password (not your Gmail password)
    mail = Mail(app)

    serializer = URLSafeTimedSerializer(app.secret_key)

    # Function to update database schema
    def update_db_schema():
        conn = get_db()
        c = conn.cursor()

        # Check if last_login column exists in users table
        c.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in c.fetchall()]

        # Add last_login column if it doesn't exist
        if 'last_login' not in columns:
            try:
                c.execute('ALTER TABLE users ADD COLUMN last_login TEXT')
                conn.commit()
                print("Added last_login column to users table")
            except Exception as e:
                print(f"Error adding last_login column: {e}")
                conn.rollback()

        # Add username column if it doesn't exist
        if 'username' not in columns:
            try:
                # First try to add without UNIQUE constraint
                c.execute('ALTER TABLE users ADD COLUMN username TEXT')
                conn.commit()
                print("Added username column to users table")
            except Exception as e:
                print(f"Error adding username column: {e}")
                conn.rollback()

        # Add gender column if it doesn't exist
        if 'gender' not in columns:
            try:
                c.execute('ALTER TABLE users ADD COLUMN gender TEXT')
                conn.commit()
                print("Added gender column to users table")
            except Exception as e:
                print(f"Error adding gender column: {e}")
                conn.rollback()

        # Add contact_number column if it doesn't exist
        if 'contact_number' not in columns:
            try:
                c.execute('ALTER TABLE users ADD COLUMN contact_number TEXT')
                conn.commit()
                print("Added contact_number column to users table")
            except Exception as e:
                print(f"Error adding contact_number column: {e}")
                conn.rollback()

        # Add address column if it doesn't exist
        if 'address' not in columns:
            try:
                c.execute('ALTER TABLE users ADD COLUMN address TEXT')
                conn.commit()
                print("Added address column to users table")
            except Exception as e:
                print(f"Error adding address column: {e}")
                conn.rollback()
    def init_db():
        conn = get_db()
        c = conn.cursor()
        
        # Users table
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            username TEXT UNIQUE,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_verified INTEGER DEFAULT 0,
            verification_token TEXT,
            created_at TEXT,
            last_login TEXT,
            date_of_birth TEXT,
            gender TEXT,
            contact_number TEXT,
            address TEXT
        )''')
        
        # User activity log table
        c.execute('''CREATE TABLE IF NOT EXISTS user_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            activity_type TEXT NOT NULL,
            activity_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            user_agent TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )''')
        
        # Create an index for faster lookups on user_id
        c.execute('''CREATE INDEX IF NOT EXISTS idx_user_activity_user_id 
                    ON user_activity (user_id)''')
        
        # Create an index for activity time
        c.execute('''CREATE INDEX IF NOT EXISTS idx_user_activity_time 
                    ON user_activity (activity_time)''')
        
        # Vaccine Schedules table
        c.execute('''CREATE TABLE IF NOT EXISTS vaccine_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vaccine_name TEXT NOT NULL,
            description TEXT,
            recommended_age TEXT NOT NULL,
            dose_number INTEGER NOT NULL,
            is_booster INTEGER DEFAULT 0,
            days_after_previous_dose INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Create an index for faster lookups on vaccine_name
        c.execute('''CREATE INDEX IF NOT EXISTS idx_vaccine_name 
                    ON vaccine_schedules (vaccine_name)''')
        
        # User Vaccine Records table
        c.execute('''CREATE TABLE IF NOT EXISTS user_vaccine_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            vaccine_schedule_id INTEGER NOT NULL,
            administered_date TEXT NOT NULL,
            administered_by TEXT,
            location TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (vaccine_schedule_id) REFERENCES vaccine_schedules (id) ON DELETE CASCADE
        )''')
        
        # Create an index for faster lookups on user_id
        c.execute('''CREATE INDEX IF NOT EXISTS idx_vaccine_record_user 
                    ON user_vaccine_records (user_id)''')
        
        # Inventory Categories table
        c.execute('''CREATE TABLE IF NOT EXISTS inventory_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Inventory Items table
        c.execute('''CREATE TABLE IF NOT EXISTS inventory_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            category_id INTEGER,
            quantity REAL NOT NULL DEFAULT 0,
            unit TEXT NOT NULL,
            min_quantity REAL DEFAULT 0,
            max_quantity REAL,
            location TEXT,
            lot_number TEXT,
            expiration_date TEXT,
            supplier_info TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES inventory_categories (id) ON DELETE SET NULL
        )''')
        
        # Inventory Transactions table
        c.execute('''CREATE TABLE IF NOT EXISTS inventory_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            transaction_type TEXT NOT NULL,  -- 'in', 'out', 'adjustment', 'expired', 'returned'
            quantity REAL NOT NULL,
            reference_type TEXT,  -- 'purchase_order', 'patient', 'waste', 'adjustment', 'expired', 'return'
            reference_id TEXT,
            notes TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (item_id) REFERENCES inventory_items (id) ON DELETE CASCADE
        )''')
        
        # Create indexes for inventory tables
        c.execute('''CREATE INDEX IF NOT EXISTS idx_inventory_items_category 
                    ON inventory_items (category_id)''')
        c.execute('''CREATE INDEX IF NOT EXISTS idx_inventory_items_name 
                    ON inventory_items (name)''')
        c.execute('''CREATE INDEX IF NOT EXISTS idx_inventory_transactions_item 
                    ON inventory_transactions (item_id)''')
        c.execute('''CREATE INDEX IF NOT EXISTS idx_inventory_transactions_date 
                    ON inventory_transactions (created_at)''')
        
        # FAQ table
        c.execute('''CREATE TABLE IF NOT EXISTS faq (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            is_active INTEGER DEFAULT 1,
            display_order INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        # Create index for faster lookups on category and active status
        c.execute('''CREATE INDEX IF NOT EXISTS idx_faq_category_active
                    ON faq (category, is_active)''')
        c.execute('''CREATE INDEX IF NOT EXISTS idx_faq_order
                    ON faq (display_order)''')

        # SMS Settings table
        c.execute('''CREATE TABLE IF NOT EXISTS sms_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            phone_number TEXT,
            appointment_reminders INTEGER DEFAULT 1,
            appointment_confirmations INTEGER DEFAULT 1,
            vaccine_reminders INTEGER DEFAULT 1,
            general_notifications INTEGER DEFAULT 1,
            marketing_messages INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )''')

        # SMS Logs table
        c.execute('''CREATE TABLE IF NOT EXISTS sms_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            phone_number TEXT NOT NULL,
            message_type TEXT NOT NULL, -- 'appointment_reminder', 'appointment_confirmation', 'vaccine_reminder', 'verification', 'marketing'
            message_content TEXT NOT NULL,
            status TEXT DEFAULT 'pending', -- 'pending', 'sent', 'failed', 'delivered'
            provider_response TEXT,
            sent_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
        )''')

        # SMS Templates table
        c.execute('''CREATE TABLE IF NOT EXISTS sms_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_name TEXT NOT NULL UNIQUE,
            message_type TEXT NOT NULL,
            template_content TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        # Archived Users table (store snapshots of deleted/archived users and related data)
        c.execute('''CREATE TABLE IF NOT EXISTS archived_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_user_id INTEGER,
            name TEXT,
            username TEXT,
            email TEXT,
            password_hash TEXT,
            is_verified INTEGER,
            created_at TEXT,
            date_of_birth TEXT,
            gender TEXT,
            contact_number TEXT,
            address TEXT,
            archived_at TEXT,
            data TEXT
        )''')

        # Create indexes for SMS tables
        c.execute('''CREATE INDEX IF NOT EXISTS idx_sms_settings_user
                    ON sms_settings (user_id)''')
        c.execute('''CREATE INDEX IF NOT EXISTS idx_sms_logs_user
                    ON sms_logs (user_id)''')
        c.execute('''CREATE INDEX IF NOT EXISTS idx_sms_logs_status
                    ON sms_logs (status)''')
        c.execute('''CREATE INDEX IF NOT EXISTS idx_sms_logs_type
                    ON sms_logs (message_type)''')

        # Insert default SMS templates if table is empty
        c.execute('SELECT COUNT(*) as count FROM sms_templates')
        if c.fetchone()['count'] == 0:
            default_templates = [
                ('appointment_reminder', 'appointment_reminder',
                 'Hi {{name}}! Reminder: You have an appointment scheduled for {{service}} on {{date}} at {{time}}. Please arrive 15 minutes early. Contact us at 0953 7207 342 if you need to reschedule.', 1),
                ('appointment_confirmation', 'appointment_confirmation',
                 'Hi {{name}}! Your appointment for {{service}} on {{date}} at {{time}} has been confirmed. See you soon! Contact: 0953 7207 342', 1),
                ('vaccine_reminder', 'vaccine_reminder',
                 'Hi {{name}}! This is a reminder for your {{vaccine_name}} vaccination. Please visit us within the next few days. Contact: 0953 7207 342', 1),
                ('verification_code', 'verification',
                 'Your verification code for Dr. Care Animal Bite Center is: {{code}}. This code expires in 10 minutes.', 1),
                ('welcome_message', 'marketing',
                 'Welcome to Dr. Care Animal Bite Center! Thank you for choosing us for your animal bite care needs. Contact us at 0953 7207 342 for any questions.', 1)
            ]
            c.executemany('INSERT INTO sms_templates (template_name, message_type, template_content, is_active) VALUES (?, ?, ?, ?)', default_templates)

        # Insert default FAQ data if table is empty
        c.execute('SELECT COUNT(*) as count FROM faq')
        if c.fetchone()['count'] == 0:
            default_faqs = [
                ('What should I do if I\'ve been bitten by an animal?', 'If you\'ve been bitten by an animal, follow these immediate steps:\n\n• Wash the wound thoroughly with soap and water for at least 15 minutes\n• Apply an antiseptic if available\n• Seek immediate medical attention at our center\n• Bring the animal if possible for observation, or note its description\n• Do not delay - rabies is a serious concern that requires prompt treatment', 'emergency', 1, 1),
                ('What are your operating hours?', 'We are open to serve you during the following hours:\n\n**Monday - Friday:** 7:00 AM to 5:00 PM\n**Saturday - Sunday:** 8:00 AM to 4:00 PM\n\n**For emergencies outside regular hours, please call:** 0953 720 7342', 'general', 1, 3),
                ('Do I need an appointment?', '**Walk-ins are welcome!** However, for faster service, we recommend:\n\n• Booking an appointment online through our website\n• Calling ahead for emergency cases\n• Arriving early, especially during peak hours\n\nAnimal bites require prompt attention, so please don\'t hesitate to visit us even without an appointment.', 'appointments', 1, 4),
                ('What should I bring for my visit?', 'Please bring the following items for your visit:\n\n• **Valid ID** (government-issued)\n• **Medical history** (if available)\n• **Insurance information** (if applicable)\n• **Payment method** (cash, GCash, or PayMaya)\n• **Pet\'s vaccination records** (if the biting animal was your pet)\n\nFor children, please bring a parent or guardian.', 'requirements', 1, 5),
                ('Do you treat all types of animal bites?', 'Yes, we treat bites from various animals including:\n\n• Dogs and cats\n• Wild animals (monkeys, bats, etc.)\n• Farm animals (horses, cows, pigs)\n• Small pets (rabbits, guinea pigs)\n• Reptiles (snakes, lizards)\n\nEach type of bite requires specific treatment protocols, especially regarding rabies risk assessment.', 'services', 1, 6),
                ('How can I contact you?', 'You can reach us through multiple channels:\n\n**Phone:** 0953 7207 342 / 0908 7029 139\n**Email:** drcareanimalbitecenternaic@gmail.com\n**Facebook:** DR. CARE ANIMAL BITE CENTER - NAIC\n**Emergency:** 0953 720 7342\n**Location:** 2nd Floor Beside Palawan Express P. Poblete St. Bgy. Gomez- Zamora Naic, Cavite (Near Naic Town Plaza)', 'contact', 1, 7),
                ('What is rabies and how dangerous is it?', 'Rabies is a viral disease that affects the nervous system and is almost always fatal once symptoms appear. It\'s transmitted through the saliva of infected animals, usually through bites, scratches, or licks on broken skin or mucous membranes. **Early treatment is critical** - if you\'ve been exposed to a potentially rabid animal, seek immediate medical attention for post-exposure prophylaxis.', 'emergency', 1, 2),
                ('What is the rabies vaccination schedule?', 'The standard post-exposure rabies vaccination schedule includes:\n\n• **Day 0:** First dose (immediately after exposure)\n• **Day 3:** Second dose\n• **Day 7:** Third dose\n• **Day 14 or 28:** Fourth dose (depending on vaccine type)\n\nFor high-risk exposures, rabies immunoglobulin (RIG) may also be administered on Day 0. Always complete the full vaccination series for maximum protection.', 'services', 1, 8),
                ('Do you provide tetanus vaccinations?', 'Yes, we provide tetanus vaccinations as part of our comprehensive wound care. Tetanus is a serious bacterial infection that can enter through animal bite wounds. We assess each case individually and administer tetanus shots when appropriate, especially if you haven\'t had a tetanus booster in the last 10 years or if your vaccination status is unknown.', 'services', 1, 9),
                ('What should I do if I\'m bitten by a stray or wild animal?', 'If bitten by a stray or wild animal:\n\n• **Do not attempt to catch or handle the animal** unless it\'s your pet\n• **Seek immediate medical care** - wild animal bites carry higher rabies risk\n• **Report the incident** to local animal control or authorities\n• **Provide detailed description** of the animal (size, color, location)\n• **Start post-exposure prophylaxis** immediately if recommended by our medical team', 'emergency', 1, 10),
                ('Can I get treatment if I don\'t have insurance?', 'Yes, we provide treatment regardless of insurance status. Payment options include:\n\n• **Cash payment**\n• **GCash**\n• **PayMaya**\n• **Payment plans** (for qualifying patients)\n• **PhilHealth coverage** (for eligible services)\n\nOur priority is your health and safety. We work with patients to find suitable payment arrangements when needed.', 'requirements', 1, 11),
                ('What is wound care and why is it important?', 'Proper wound care after an animal bite is crucial because:\n\n• **Prevents infection** - Animal mouths contain many bacteria\n• **Promotes healing** - Clean wounds heal faster and better\n• **Reduces scarring** - Proper care minimizes tissue damage\n• **Monitors for complications** - Early detection of infection or other issues\n\nOur wound care includes cleaning, debridement, antibiotic assessment, and follow-up instructions.', 'services', 1, 12),
                ('How do I know if I need rabies immunoglobulin (RIG)?', 'Rabies immunoglobulin (RIG) is recommended for:\n\n• **Severe exposures** (multiple bites, deep wounds, bites to face/head)\n• **Immunocompromised individuals**\n• **Delayed presentation** (more than 24-48 hours after exposure)\n• **High-risk animal exposures** (bats, wild carnivores, unknown/stray animals)\n\nOur medical team assesses each case individually based on exposure details and current health guidelines.', 'services', 1, 13),
                ('What are the signs of rabies infection?', 'Early symptoms of rabies may include:\n\n• **Flu-like symptoms** (fever, headache, fatigue)\n• **Pain or tingling** at the bite site\n• **Anxiety and confusion**\n• **Difficulty swallowing**\n• **Excessive salivation**\n• **Hydrophobia** (fear of water)\n• **Hallucinations**\n\n**Once symptoms appear, rabies is almost always fatal.** This is why immediate post-exposure treatment is critical.', 'emergency', 1, 14),
                ('Do you offer follow-up care?', 'Yes, we provide comprehensive follow-up care including:\n\n• **Wound check appointments**\n• **Vaccination completion**\n• **Scar management**\n• **Psychological support** (if needed after traumatic incidents)\n• **Complication monitoring**\n• **Vaccination records** for your personal health file\n\nWe recommend follow-up visits 3-7 days after initial treatment and for each vaccination dose.', 'services', 1, 15),
                ('Can children receive treatment at your center?', 'Yes, we treat patients of all ages, including children. For pediatric patients:\n\n• **Parental consent required**\n• **Age-appropriate explanations** and care\n• **Child-friendly environment**\n• **Specialized dosing** for medications and vaccines\n• **Comfort measures** during procedures\n\nChildren may respond differently to animal bites, so we take extra care to ensure they feel safe and comfortable.', 'general', 1, 16),
                ('What is post-exposure prophylaxis (PEP)?', 'Post-exposure prophylaxis (PEP) is the immediate treatment given after potential rabies exposure. It includes:\n\n• **Wound cleaning and care**\n• **Rabies vaccination series**\n• **Rabies immunoglobulin (RIG)** if indicated\n• **Tetanus vaccination** if needed\n• **Antibiotic prophylaxis** for wound infection prevention\n\nPEP is highly effective when administered promptly after exposure. The sooner treatment begins, the better the protection.', 'services', 1, 17),
                ('How can I prevent animal bites?', 'Prevention tips to avoid animal bites:\n\n• **Never approach unfamiliar animals**\n• **Teach children** not to pet strange animals\n• **Keep pets vaccinated** and under control\n• **Avoid wild animals** and their habitats\n• **Don\'t disturb animals** while eating or sleeping\n• **Report stray animals** to local authorities\n• **Use caution around** sick or injured animals\n\nRemember: most bites occur from familiar pets or during attempts to help animals.', 'general', 1, 18),
                ('What should I do if my pet bites someone?', 'If your pet bites someone:\n\n• **Ensure the victim seeks medical care** immediately\n• **Quarantine your pet** for 10-14 days observation\n• **Provide vaccination records** to the victim\'s healthcare provider\n• **Cooperate with animal control** if contacted\n• **Consider behavioral assessment** for your pet\n• **Update vaccinations** if needed\n\nHonest reporting helps protect both the victim and your pet\'s well-being.', 'general', 1, 19),
                ('Do you provide vaccination records or certificates?', 'Yes, we provide official documentation for all vaccinations and treatments including:\n\n• **Vaccination certificates** with dates and lot numbers\n• **Treatment summaries**\n• **International Health Certificates** (if traveling)\n• **Digital records** accessible through our patient portal\n• **Reminder cards** for follow-up doses\n\nThese records are important for travel, school, work, and personal health tracking.', 'services', 1, 20)
            ]
            c.executemany('INSERT INTO faq (question, answer, category, is_active, display_order) VALUES (?, ?, ?, ?, ?)', default_faqs)

    # Initialize database and routes.
    # If DATABASE_URL is set we assume a managed DB will be used and skip the automatic SQLite init.
    with app.app_context():
        if not os.environ.get('DATABASE_URL'):
            # Initialize the database (sqlite) and apply schema updates
            init_db()
            update_db_schema()

        # Initialize routes
        init_routes(app, get_db, mail, serializer)
        init_document_routes(app, get_db)
        init_inventory_routes(app, get_db)
        init_services_routes(app, get_db)
        init_appointments_routes(app, get_db)
        init_calendar_routes(app, get_db)
    
    # Add datetime filter to Jinja2 environment
    def datetimeformat(value, format='%Y-%m-%d %H:%M'):
        if value is None:
            return ''
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    value = datetime.strptime(value, '%Y-%m-%d')
                except ValueError:
                    return value
        return value.strftime(format)

    app.jinja_env.filters['datetimeformat'] = datetimeformat

    # Initialize SMS service
    sms_service = SMSService(app)

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)

