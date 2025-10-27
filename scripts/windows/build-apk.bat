@echo off
echo ========================================
echo Dr. Care TWA APK Build Script
echo ========================================
echo.

REM Check if Android Studio is installed
if not exist "%ANDROID_HOME%" (
    echo ERROR: ANDROID_HOME environment variable not set
    echo Please install Android Studio and set up environment variables
    echo.
    echo To set up:
    echo 1. Install Android Studio
    echo 2. Set ANDROID_HOME to Android SDK path
    echo 3. Add platform-tools and tools to PATH
    echo.
    pause
    exit /b 1
)

echo Building APK...
echo.

REM Navigate to TWA directory
cd android-twa

REM Build debug APK
echo Building debug APK...
call gradlew assembleDebug

if %errorlevel% neq 0 (
    echo ERROR: Debug build failed
    pause
    exit /b 1
)

REM Build release APK
echo Building release APK...
call gradlew assembleRelease

if %errorlevel% neq 0 (
    echo ERROR: Release build failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo BUILD SUCCESSFUL!
echo ========================================
echo.
echo APK files created in:
echo - Debug: android-twa\app\build\outputs\apk\debug\
echo - Release: android-twa\app\build\outputs\apk\release\
echo.
echo Next steps:
echo 1. Test the APK on your Android device
echo 2. Generate a signed APK for Play Store
echo 3. Update yourdomain.com with your actual domain
echo 4. Configure Digital Asset Links
echo.
pause
