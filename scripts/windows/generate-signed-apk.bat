@echo off
echo ========================================
echo Dr. Care - Generate Signed APK
echo ========================================
echo.

REM Check if keystore exists
if not exist "drcare-key.jks" (
    echo Creating new keystore...
    echo.
    echo IMPORTANT: You'll need to provide keystore information
    echo - Key alias: drcare
    - Keystore password: (remember this!)
    echo - Key password: (can be same as keystore)
    echo - First/Last name: Your name
    echo - Organization: Dr. Care Animal Bite Center
    echo - City: Your city
    echo - State: Your state
    echo - Country: PH (Philippines)
    echo.
    echo Press any key to continue...
    pause >nul

    keytool -genkeypair -v ^
        -keystore drcare-key.jks ^
        -keyalg RSA ^
        -keysize 2048 ^
        -validity 10000 ^
        -alias drcare ^
        -dname "CN=Dr Care, OU=Medical, O=Dr Care Animal Bite Center, L=Naic, S=Cavite, C=PH"

    if %errorlevel% neq 0 (
        echo ERROR: Failed to create keystore
        pause
        exit /b 1
    )

    echo.
    echo Keystore created successfully!
    echo IMPORTANT: Keep drcare-key.jks safe and remember the passwords!
    echo.
    pause
)

echo.
echo Building signed release APK...
echo.

REM Navigate to TWA directory
cd android-twa

REM Build signed release APK
call gradlew assembleRelease ^
    -Pandroid.injected.signing.store.file=../drcare-key.jks ^
    -Pandroid.injected.signing.store.password=STORE_PASSWORD_HERE ^
    -Pandroid.injected.signing.key.alias=drcare ^
    -Pandroid.injected.signing.key.password=KEY_PASSWORD_HERE

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Build failed. You need to set the passwords.
    echo.
    echo To fix this, edit this batch file and replace:
    echo - STORE_PASSWORD_HERE with your keystore password
    echo - KEY_PASSWORD_HERE with your key password
    echo.
    echo Or build manually with Android Studio.
    pause
    exit /b 1
)

echo.
echo ========================================
echo SIGNED APK GENERATED!
echo ========================================
echo.
echo Your signed APK is ready for Google Play Store:
echo Location: android-twa\app\build\outputs\apk\release\app-release.apk
echo.
echo Next steps:
echo 1. Test the APK on multiple devices
echo 2. Create Google Play Console account
echo 3. Upload APK to Play Store
echo 4. Fill in store listing details
echo 5. Publish your app!
echo.
echo Remember to keep your keystore file (drcare-key.jks) safe!
echo You'll need it for all future app updates.
echo.
pause
