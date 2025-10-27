@echo off
echo ========================================
echo Dr. Care APK Testing Setup
echo ========================================
echo.

REM Check if Android Studio is installed
if not exist "%ANDROID_HOME%" (
    echo ERROR: ANDROID_HOME not set
    echo Please install Android Studio first
    echo.
    echo Download: https://developer.android.com/studio
    echo.
    pause
    exit /b 1
)

echo Setting up Android Emulator...
echo.

REM Navigate to TWA directory
cd android-twa

REM Build debug APK first
echo Building debug APK...
call gradlew assembleDebug

if %errorlevel% neq 0 (
    echo ERROR: Failed to build debug APK
    echo Make sure Android SDK is properly installed
    pause
    exit /b 1
)

echo.
echo ========================================
echo SETUP COMPLETE!
echo ========================================
echo.
echo Next steps:
echo 1. Open Android Studio
echo 2. Go to Tools > Device Manager
echo 3. Create a new Virtual Device
echo 4. Run the emulator
echo 5. Drag APK to emulator to install
echo.
echo Your debug APK is ready at:
echo android-twa\app\build\outputs\apk\debug\app-debug.apk
echo.
pause
