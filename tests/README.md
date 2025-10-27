# tests/

This folder contains project unit/integration test files that were moved from the repository root to keep the root directory tidy.

Purpose
- Group all `test_*.py` files so test tools (pytest, CI) can discover them easily.

How to run
- Using pytest (recommended):
  - Install dev dependencies (if any) then run `pytest tests/` from the repository root.

Restore (undo)
To move the files back to the repository root, run this PowerShell command from the project root:

```powershell
Get-ChildItem -Path .\tests\* -File | ForEach-Object { Move-Item -Path $_.FullName -Destination .\ -Force }
```

Notes
- These files are considered development-only. They may reference dev-only packages not present in production.
