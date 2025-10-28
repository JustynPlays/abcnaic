# SQLite -> Postgres migration helper

This repository includes a helper that copies the schema and data from a local
SQLite file into a Postgres database (useful for migrating to Heroku Postgres).

Files added
- `scripts/sqlite_to_postgres.py` — Python script that reflects the SQLite
  schema and copies data into the target Postgres database using SQLAlchemy.
- `scripts/run_migration.ps1` — PowerShell wrapper that calls the Python script
  and reads `DATABASE_URL` from the environment if present.

Dependencies
- `SQLAlchemy>=1.4` (already added to `requirements.txt`)
- `psycopg2-binary` (for Postgres driver; already present in `requirements.txt`)

Quick usage (PowerShell)

1) Install dependencies

```powershell
python -m pip install -r requirements.txt
```

2) Run migration using `DATABASE_URL` from env (recommended when migrating to
   Heroku; Heroku sets `DATABASE_URL` for you):

```powershell
# On Windows PowerShell (if DATABASE_URL is in env):
python .\scripts\sqlite_to_postgres.py --sqlite .\db\app.db

# Or pass the Postgres URL explicitly:
python .\scripts\sqlite_to_postgres.py --sqlite .\db\app.db --pg "postgres://user:pass@host:5432/dbname"
```

3) Or use the provided helper:

```powershell
.\scripts\run_migration.ps1 -Sqlite db\app.db
```

Notes and caveats
- Always test the migration against a copy of your database first.
- This helper attempts to create the tables in Postgres and then bulk-inserts
  rows from SQLite. It will also attempt to set SERIAL sequences for integer
  `id` primary keys when possible.
- The script does not attempt to transform complex SQLite-specific types or
  user-defined functions. Manual verification is required for correctness.
- If you have custom migrations or schema differences, handle them before or
  after copying data.

If you want, I can:
- Add a dry-run mode that prints the tables and counts without inserting.
- Create a one-off script to export a dump that you can run on Heroku (`heroku run`).
- Add an option to skip certain tables during copy.
