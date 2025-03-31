@echo off
echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Launching Unified Admin GUI...
python unified_admin.py

if errorlevel 1 (
    echo Error occurred while running the application.
    echo Please check the logs for more information.
    pause
    exit /b 1
)

exit /b 0 