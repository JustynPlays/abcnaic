import pymysql
import os

def update_flask_config():
    """Update Flask app configuration to use MySQL"""

    app_py_content = '''import os
import sqlite3
from flask import Flask
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail
from routes import init_routes
from routes_user_documents import init_document_routes
from routes_inventory import init_inventory_routes
from routes_services import init_services_routes
from routes_appointments import init_appointments_routes
from routes_calendar import init_calendar_routes
from datetime import datetime

def create_app():
    app = Flask(__name__)
    app.secret_key = os.urandom(24)

    # MySQL Database setup (updated configuration)
    def get_db():
        return pymysql.connect(
            host='localhost',
            user='root',
            password='',  # Update if you have a MySQL password
            database='animal_bite_center',
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )

    # Store the get_db function in app context for use in routes
    app.get_db = get_db

    # Mail setup (update with your email credentials)
    app.config['MAIL_SERVER'] = 'smtp.gmail.com'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'your_email@gmail.com'  # Update with your Gmail
    app.config['MAIL_PASSWORD'] = 'your_app_password'     # Update with App Password
    mail = Mail(app)

    serializer = URLSafeTimedSerializer(app.secret_key)

    # Initialize routes (pass mail and serializer)
    init_routes(app, get_db, mail, serializer)
    init_document_routes(app, get_db, mail, serializer)
    init_inventory_routes(app, get_db, mail, serializer)
    init_services_routes(app, get_db, mail, serializer)
    init_appointments_routes(app, get_db, mail, serializer)
    init_calendar_routes(app, get_db, mail, serializer)

    return app

# For development server
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
'''

    # Write the updated app.py
    with open('app_mysql.py', 'w', encoding='utf-8') as f:
        f.write(app_py_content)

    print("✅ Created app_mysql.py with MySQL configuration")
    print("📝 Next steps:")
    print("   1. Update the MySQL credentials in app_mysql.py")
    print("   2. Update email settings in app_mysql.py")
    print("   3. Run: python app_mysql.py")
    print("   4. Access your app at: http://localhost:5000")

if __name__ == "__main__":
    update_flask_config()
