@echo off
echo ========================================
echo Dr. Care - Build Test
echo ========================================
echo.
echo Testing if Android project builds correctly...
echo.
cd android-twa
call gradlew.bat assembleDebug

if %errorlevel% neq 0 (
    echo.
    echo ❌ BUILD FAILED
    echo.
    echo Common solutions:
    echo 1. Install Android Studio
    echo 2. Set ANDROID_HOME environment variable
    echo 3. Run troubleshoot-emulator.bat
    echo 4. Check Java installation
    echo.
    echo Try running troubleshoot-emulator.bat first
    echo.
    pause
    exit /b 1
)

echo.
echo ✅ BUILD SUCCESSFUL!
echo.
echo Your APK is ready at:
echo android-twa\app\build\outputs\apk\debug\app-debug.apk
echo.
echo Next steps:
echo 1. Install Android Studio emulator
echo 2. Run quick-test.bat to test with emulator
echo 3. Or use third-party emulators like BlueStacks
echo.
echo Press any key to open the APK location...
pause >nul
explorer "app\build\outputs\apk\debug"
echo.
echo APK location opened in file explorer.
pause
