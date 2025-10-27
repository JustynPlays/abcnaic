@echo off
echo ========================================
echo Dr. Care - Quick APK Test
echo ========================================
echo.
echo This script will:
echo 1. Build the debug APK
echo 2. Start Android Emulator
echo 3. Install APK automatically
echo.
echo Press any key to continue...
pause >nul

echo.
echo Building APK...
cd android-twa
call gradlew.bat assembleDebug

if %errorlevel% neq 0 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo.
echo Starting Android Emulator...
echo (This may take a few minutes...)
start "" "C:\Program Files\Android\Android Studio\emulator\emulator.exe" -avd Pixel_3a_API_30

echo.
echo Waiting for emulator to start...
timeout /t 30 /nobreak >nul

echo.
echo Installing APK on emulator...
adb install -r app/build/outputs/apk/debug/app-debug.apk

if %errorlevel% neq 0 (
    echo.
    echo WARNING: Could not install automatically
    echo Please drag the APK to emulator manually:
    echo Location: android-twa\app\build\outputs\apk\debug\app-debug.apk
    echo.
) else (
    echo.
    echo SUCCESS! APK installed on emulator
    echo Look for "Dr. Care Animal Bite Center" in app drawer
    echo.
)

echo.
echo Emulator should be running now!
echo Test your app and check for any issues.
echo.
pause
