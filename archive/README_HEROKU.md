# Heroku deployment (ABC-PWA Ichatbot)

This document describes the minimal steps to deploy this Flask app to Heroku.

Prerequisites
- Heroku account (https://www.heroku.com/) and Heroku CLI installed.
- Git installed and repository committed.

Files added for Heroku
- `Procfile` — starts the web process using gunicorn:
  ```
  web: gunicorn app:app --log-file -
  ```
  (Assumes `app.py` defines `app` WSGI application.)

- `runtime.txt` — Python runtime used by Heroku (example `python-3.11.6`).

- `requirements.txt` — contains project dependencies; `gunicorn` has been added.

Quick deploy steps (PowerShell)
1. Login and create app
```powershell
heroku login
cd "C:\xampp2\htdocs\ABC-PWA Ichatbot"
# ensure repo is initialized and committed
git init
git add .
git commit -m "Prepare for Heroku"
heroku create your-app-name
```

2. Add Postgres and Redis (optional but recommended)
```powershell
heroku addons:create heroku-postgresql:hobby-dev --app your-app-name
heroku addons:create heroku-redis:hobby-dev --app your-app-name
```

3. Set config vars (example for Twilio)
```powershell
heroku config:set TWILIO_ACCOUNT_SID="ACxxxxxxxx" TWILIO_AUTH_TOKEN="your_auth_token" TWILIO_FROM="+1xxxxxxxx" --app your-app-name
```

4. Push to Heroku
```powershell
git push heroku main
```

5. Run migrations / one-off commands
```powershell
heroku run python scripts/your_migration_script.py --app your-app-name
```

6. View logs and open app
```powershell
heroku logs --tail --app your-app-name
heroku open --app your-app-name
```

Notes & recommendations
- Heroku dynos have ephemeral filesystem — migrate from SQLite to Postgres for persistence.
- Keep secrets (TWILIO_*, REDIS_URL) in Heroku config vars — never commit them to source control.
- If your Flask entry point is not `app.py`/`app`, update the command in the `Procfile` accordingly (e.g., `web: gunicorn "routes:create_app()"`).

If you want, I can:
- Add a `Procfile` command tailored to a different entrypoint if needed.
- Create a migration helper to export your SQLite DB and import to Heroku Postgres.
- Walk you through the exact Heroku commands step-by-step in your terminal.
