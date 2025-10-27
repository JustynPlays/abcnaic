@echo off
echo ========================================
echo Dr. Care - Emulator Troubleshooter
echo ========================================
echo.
echo This will help fix common emulator issues
echo.
echo Press any key to start troubleshooting...
pause >nul

echo.
echo === CHECKING ANDROID SDK ===
if not exist "%ANDROID_HOME%" (
    echo ERROR: ANDROID_HOME not set
    echo Please install Android Studio and set environment variables
    echo.
    echo To fix:
    echo 1. Install Android Studio
    echo 2. Set ANDROID_HOME to SDK path
    echo 3. Add platform-tools to PATH
    echo.
    goto :emulator_check
)

echo Android SDK found: %ANDROID_HOME%
echo.

:emulator_check
echo === CHECKING EMULATOR ===
if not exist "%ANDROID_HOME%\emulator\emulator.exe" (
    echo ERROR: Emulator not found
    echo Please install Android Emulator through Android Studio
    echo.
    echo To fix:
    echo 1. Open Android Studio
    echo 2. Tools > SDK Manager
    echo 3. Install Android Emulator
    echo.
    goto :avd_check
)

echo Emulator found
echo.

:avd_check
echo === CHECKING VIRTUAL DEVICES ===
avdmanager list avd

if %errorlevel% neq 0 (
    echo No virtual devices found
    echo Creating a default AVD...
    echo.
    avdmanager create avd -n "Pixel_3a_API_30" -k "system-images;android-30;google_apis;x86"
    if %errorlevel% neq 0 (
        echo ERROR: Could not create AVD
        echo Please create manually in Android Studio
        echo.
        goto :cleanup
    )
    echo AVD created successfully!
)

echo.
echo === CHECKING ADB ===
adb devices

echo.
echo === CLEANUP RECOMMENDATIONS ===
echo If emulator still has issues:
echo 1. Close all emulators
echo 2. Run: adb kill-server && adb start-server
echo 3. Wipe emulator data in Device Manager
echo 4. Restart computer if needed
echo.

:cleanup
echo.
echo === COMMON FIXES ===
echo.
echo Fix 1: Restart ADB server
echo Command: adb kill-server ^&^& adb start-server
echo.
echo Fix 2: Wipe emulator data
echo - In Android Studio: Tools > Device Manager
echo - Right-click device > Wipe Data
echo.
echo Fix 3: Cold boot emulator
echo - Close emulator completely
echo - Restart from Device Manager
echo.
echo Fix 4: Check virtualization
echo - Enable VT-x in BIOS/UEFI
echo - Restart computer
echo.
echo Fix 5: Reinstall HAXM
echo - SDK Manager > SDK Tools > Intel x86 Emulator Accelerator
echo.

echo.
echo ========================================
echo Troubleshooting complete!
echo ========================================
echo.
echo If issues persist:
echo 1. Try the quick-test.bat script
echo 2. Create a new AVD in Android Studio
echo 3. Check Android Studio logs
echo.
pause
