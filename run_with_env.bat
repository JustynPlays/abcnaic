@echo off
REM run_with_env.bat — set env vars for testing and call existing run_flask.bat
REM Copy this file next to run_flask.bat and edit the placeholders below.

:: Replace these with your Twilio credentials and number (E.164 format)
set TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxx
set TWILIO_AUTH_TOKEN=your_auth_token_here
set TWILIO_FROM=+14246552211
set TWILIO_VERIFY_SERVICE_SID=
set REDIS_URL=redis://localhost:6379/0

:: Optional: set SMS_PROVIDER if your code supports provider switching
rem set SMS_PROVIDER=twilio

:: Call existing runner (doesn't modify run_flask.bat)
call "%~dp0run_flask.bat"
