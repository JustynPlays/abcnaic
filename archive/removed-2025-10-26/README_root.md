# Animal Bite Center - User Portal

A simple, modern web app for user registration, login, and email verification for the Animal Bite Center. Red and white themed.

## Features
- Landing page with branding
- User registration (with email verification)
- User login (only after verification)
- SQLite backend
- Flask-based backend

## Setup Instructions

1. **Clone or copy the code** to your local server directory (e.g., `c:/xampp2/htdocs/ABC`).

2. **Install dependencies**:

```bash
pip install -r requirements.txt
```

3. **Configure Email**:
- In `app.py`, set `MAIL_USERNAME` and `MAIL_PASSWORD` to your Gmail or SMTP credentials.
- If using Gmail, you may need to enable "App Passwords".

4. **Run the app**:

```bash
python app.py
```

5. **Open your browser** to [http://localhost:5000](http://localhost:5000)

## Notes
- Database is auto-initialized on first run in `/db/users.db`.
- Email verification links expire in 1 hour.
- Only verified users can log in.

---

**For production, use a real SMTP server and secure your secret keys.**
