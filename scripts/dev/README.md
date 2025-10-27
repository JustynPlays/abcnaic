# scripts/dev/

This folder contains developer helper scripts and small maintenance utilities.

Typical files
- `debug_routes.py`, `analyze_db.py`, `add_columns.py` — quick utilities used while developing or debugging.

Usage
- Inspect the scripts before running. They may modify the database or application files.

Restore (undo)
```powershell
Get-ChildItem -Path .\scripts\dev\* -File | ForEach-Object { Move-Item -Path $_.FullName -Destination .\ -Force }
```

Notes
- Keep these scripts in `scripts/dev` to make the repo root cleaner. Consider versioning longer-term helpers in a tools/ folder.
