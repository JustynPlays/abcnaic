# scripts/windows/

This folder groups Windows batch helpers and build/development scripts.

Examples
- `build-apk.bat`, `generate-signed-apk.bat`, `setup-emulator.bat`, `troubleshoot-emulator.bat`, `check_xampp.bat`, etc.

Usage
- Run these `.bat` scripts from a Windows shell when performing the associated tasks. Keep them here so the repository root is less cluttered.

Restore (undo)
```powershell
Get-ChildItem -Path .\scripts\windows\* -File | ForEach-Object { Move-Item -Path $_.FullName -Destination .\ -Force }
```

Notes
- These scripts are platform-specific and typically not used in CI or on non-Windows hosts.
