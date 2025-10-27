# checks/

This folder contains diagnostic and ad-hoc check scripts (files named `check_*.py`) moved from the project root.

Purpose
- Keep diagnostic scripts separate from application code.

Usage
- These scripts are typically intended for local development or debugging only. Inspect each file before running.

Restore (undo)
```powershell
Get-ChildItem -Path .\checks\* -File | ForEach-Object { Move-Item -Path $_.FullName -Destination .\ -Force }
```

Notes
- Some check scripts assume developer-installed packages. Run them in a dev environment or virtualenv.
