DigitalOcean deployment notes (Droplet / App Platform)
===============================================

This project is a Flask app. Below are two deployment options for DigitalOcean:

1) Quick: single Droplet running Docker (recommended for now)
-----------------------------------------------------------
- Create an Ubuntu Droplet (recommended region: Singapore `sgp1` for PH users).
- SSH into the Droplet, install Docker and Docker Compose.

  # Install Docker (on Ubuntu)
  sudo apt update && sudo apt install -y docker.io docker-compose
  sudo systemctl enable --now docker

- Copy your repo to the Droplet (git clone or push). Build and run with docker-compose:

  docker-compose build --no-cache
  docker-compose up -d

- Volumes:
  - `./db` is mounted to `/app/db` in the container so SQLite persists across restarts.
  - `./static/uploads` is mounted to `/app/static/uploads` to persist uploaded files.

- Set environment variables in the Droplet or a `.env` file (SECRET_KEY, MAIL_USERNAME, MAIL_PASSWORD).

# Pros
- Simple, low management overhead, you keep using SQLite and existing code.

# Cons
- Single point of failure, limited scaling. For production use a managed database.

2) App Platform (managed) — recommended for easy scaling
------------------------------------------------------
- Use DigitalOcean App Platform, connect your GitHub repo, and choose "Dockerfile" as the build method (we included a Dockerfile).
- Set the build and run environment variables in the App Platform UI (SECRET_KEY, MAIL_USERNAME, MAIL_PASSWORD, etc.).
- For persistence you should provision a Managed Database (Postgres or MySQL) and update the app to use it (see below).

# App Platform pros
- Zero-ops deployment, automatic TLS, simple environment variable management, auto-deploy from GitHub.

# Important notes about storage & DB
- App Platform containers have ephemeral local storage. Do NOT rely on SQLite for production there.
- Recommended production stack: Managed Postgres (DigitalOcean) + Spaces for file uploads.
- If you want to keep using SQLite, deploy to a Droplet and mount the `db` folder.

Switching to a managed DB (high level)
--------------------------------------
1. Provision a Managed Postgres or MySQL instance on DigitalOcean.
2. Export your SQLite data and import into the managed DB (there are conversion tools; I can prepare one).
3. Update `app.py` to use an env var (e.g., `DATABASE_URL`) and a Postgres client (psycopg2 or async library) or use SQLAlchemy.

Environment variables the app expects (configure these in App Platform or on Droplet):
- SECRET_KEY — random secret for Flask sessions
- MAIL_USERNAME — SMTP username
- MAIL_PASSWORD — SMTP password (app password)
- (Optional) DATABASE_URL — if you migrate to Postgres
- PORT — (5000 by default)

Next steps I can do for you
- Add migration script (SQLite → Postgres) and modify `app.py` to support `DATABASE_URL`.
- Create a small `docker-compose.prod.yml` to run NGiNX in front of Gunicorn and optionally Let's Encrypt.
- Walk you through creating a Droplet and running the compose commands step-by-step.
