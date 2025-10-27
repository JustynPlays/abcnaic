@echo off
REM Ensure a virtual environment exists and activate it
IF NOT EXIST venv (
    echo Creating virtual environment venv...
    python -m venv venv
)
call venv\Scripts\activate

REM Upgrade pip and install requirements into the venv
python -m pip install --upgrade pip
echo Installing Python packages (quiet mode). If this fails, full pip output will be shown.
echo Using python at: 
where python
echo pip version: 
python -m pip --version

REM Try quiet install first to reduce noise in the console
python -m pip install --disable-pip-version-check -r requirements.txt -q >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Quiet install failed, running pip without quiet to show errors/output...
    python -m pip install --disable-pip-version-check -r requirements.txt
) else (
    echo Dependencies installed.
)

REM Run the Flask app
python app.py

pause
