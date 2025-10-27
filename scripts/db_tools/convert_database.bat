@echo off
echo ========================================
echo SQLite to MySQL Database Converter
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ✗ Python is not installed or not in PATH
    echo Please install Python to run the conversion script
    pause
    exit /b 1
)

REM Check if required Python packages are installed
python -c "import pymysql" >nul 2>&1
if errorlevel 1 (
    echo Installing required packages...
    pip install pymysql
    if errorlevel 1 (
        echo ✗ Failed to install pymysql
        echo Please run: pip install pymysql
        pause
        exit /b 1
    )
)

echo Starting database conversion...
python sqlite_to_mysql_converter.py

if %errorlevel% equ 0 (
    echo.
    echo ✅ Conversion completed successfully!
    echo.
    echo Your data has been converted from SQLite to MySQL.
    echo You can now:
    echo - Use phpMyAdmin to view the data
    echo - Update your Flask app to use MySQL instead of SQLite
    echo - Access your app through XAMPP
    echo.
) else (
    echo.
    echo ⚠️  Conversion completed with errors.
    echo Please check the error messages above.
    echo.
)

echo Press any key to continue...
pause >nul
