@echo off
echo Checking for XAMPP installation...

REM Check common XAMPP installation paths
if exist "c:\xampp" (
    echo ✓ XAMPP found in c:\xampp
    goto :xampp_found
)

if exist "c:\Program Files\xampp" (
    echo ✓ XAMPP found in c:\Program Files\xampp
    goto :xampp_found
)

if exist "c:\Program Files (x86)\xampp" (
    echo ✓ XAMPP found in c:\Program Files (x86)\xampp
    goto :xampp_found
)

echo ✗ XAMPP not found in standard locations
echo Please install XAMPP or update the paths in this script
pause
exit /b 1

:xampp_found
echo.
echo === XAMPP Setup Instructions ===
echo.
echo 1. Start XAMPP Control Panel
echo 2. Start Apache and MySQL modules
echo 3. Open browser and go to: http://localhost/phpmyadmin
echo 4. Create a new database called 'animal_bite_center'
echo 5. Run the conversion script
echo.
echo === Manual Database Creation ===
echo If phpMyAdmin doesn't work, run this in Command Prompt:
echo "c:\xampp\mysql\bin\mysql.exe" -u root -e "CREATE DATABASE animal_bite_center;"
echo.
pause
