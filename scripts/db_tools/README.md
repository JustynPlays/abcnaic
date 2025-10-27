# scripts/db_tools/

This directory contains database-related helper scripts and small utilities that were moved out of the repository root.

Files here may include:
- `sqlite_to_mysql_converter.py` — helper for converting SQLite databases to MySQL.
- `create_mysql_config.py` — utility to create MySQL connection configs.
- `convert_database.bat` — Windows wrapper for conversion tasks.

Usage
- Run these scripts in a development environment with the required DB clients installed. Review each script for credentials before executing.

Restore (undo)
```powershell
Get-ChildItem -Path .\scripts\db_tools\* -File | ForEach-Object { Move-Item -Path $_.FullName -Destination .\ -Force }
```

Notes
- If you plan to migrate to a managed Postgres database, prefer using `scripts/migrate_sqlite_to_postgres.py` (root `scripts/`).
