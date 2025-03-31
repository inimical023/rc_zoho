@echo off
setlocal enabledelayedexpansion

echo Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo Error: Failed to activate virtual environment.
    echo Please ensure the virtual environment is properly installed.
    echo Run setup_integration.bat to set up the environment.
    pause
    exit /b 1
)

echo Launching Unified Admin GUI...
python unified_admin.py
if errorlevel 1 (
    echo Error: Application failed to start.
    echo Please check the logs in the logs directory for more information.
    echo Common issues:
    echo - Missing or invalid credentials
    echo - Network connectivity issues
    echo - Python environment problems
    pause
    exit /b 1
)

exit /b 0 