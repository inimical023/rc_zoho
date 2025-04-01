@echo off
setlocal enabledelayedexpansion

:: Create logs directory if it doesn't exist
if not exist logs mkdir logs

:: Set up logging
set "log_file=logs\setup_integration_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%.log"

:: Define the log function at the beginning but skip over it using GOTO
goto :start_script

:log
echo %~1 >> "%log_file%"
echo %~1
exit /b 0

:download_file
set filename=%~1
set url=%~2
call :log "Downloading %filename%..."
curl -s -o %filename% "%url%" >> "%log_file%" 2>&1
if errorlevel 1 (
    call :log "Failed to download %filename% from %url%"
    call :log "Retrying with alternative method..."
    powershell -Command "Invoke-WebRequest -Uri '%url%' -OutFile '%filename%'" >> "%log_file%" 2>&1
    if errorlevel 1 (
        call :log "Failed to download %filename% after retry"
        exit /b 1
    )
)
call :log "Successfully downloaded %filename%"
exit /b 0

:start_script
:: Start logging
call :log "=========================================================="
call :log "  RingCentral-Zoho Integration Setup"
call :log "=========================================================="
call :log ""

:: Log the file creation time using a more compatible approach
call :log "Setup script path: %~f0"
call :log "Setup script timestamp: %date% %time%"

:: Verify GitHub connectivity
call :log "Verifying GitHub connectivity..."
curl -s -o nul -w "%%{http_code}" https://raw.githubusercontent.com/inimical023/rc_zoho/main/README.md > github_status.txt
set /p github_status=<github_status.txt
del github_status.txt

if not "%github_status%"=="200" (
    call :log "ERROR: Cannot access GitHub repository. Status code: %github_status%"
    call :log "Please check your internet connection and try again."
    pause
    exit /b 1
)

call :log "GitHub repository is accessible. Continuing setup..."

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    call :log "Python is not installed. Please install Python 3.8 or later."
    pause
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist .venv (
    call :log "Creating virtual environment..."
    python -m venv .venv >> "%log_file%" 2>&1
    if errorlevel 1 (
        call :log "Failed to create virtual environment."
        pause
        exit /b 1
    )
)

:: Activate virtual environment
call :log "Activating virtual environment..."
call .venv\Scripts\activate.bat
if errorlevel 1 (
    call :log "Failed to activate virtual environment."
    pause
    exit /b 1
)

:: Install required packages
call :log "Installing required packages..."
python -m pip install --upgrade pip >> "%log_file%" 2>&1
python -m pip install "setuptools>=40.0.0" >> "%log_file%" 2>&1
python -m pip install "tkcalendar>=1.6.0" >> "%log_file%" 2>&1

:: Check if requirements.txt exists
if exist requirements.txt (
    call :log "Found requirements.txt, installing dependencies..."
    pip install -r requirements.txt >> "%log_file%" 2>&1
) else (
    call :log "Creating a basic requirements.txt file..."
    echo requests>=2.25.1 > requirements.txt
    echo python-dotenv>=0.15.0 >> requirements.txt
    echo cryptography>=3.4.6 >> requirements.txt
    echo pywin32>=300 >> requirements.txt
    echo pytz>=2021.1 >> requirements.txt
    echo python-dateutil>=2.8.1 >> requirements.txt
    echo urllib3>=1.26.4 >> requirements.txt
    echo tkcalendar>=1.6.1 >> requirements.txt
    pip install -r requirements.txt >> "%log_file%" 2>&1
)

:: Verify package installation
call :log "Verifying package installation..."
echo import setuptools > verify_packages.py
echo import cryptography >> verify_packages.py
echo import os >> verify_packages.py
echo try: >> verify_packages.py
echo     import dotenv >> verify_packages.py
echo     print("dotenv: OK") >> verify_packages.py
echo except ImportError: >> verify_packages.py
echo     print("dotenv: Not found, but may be fine") >> verify_packages.py
echo import requests >> verify_packages.py
echo import dateutil >> verify_packages.py
echo import pytz >> verify_packages.py
echo import urllib3 >> verify_packages.py
echo import certifi >> verify_packages.py
echo import charset_normalizer >> verify_packages.py
echo import idna >> verify_packages.py
echo print("All core packages verified!") >> verify_packages.py

python verify_packages.py >> "%log_file%" 2>&1
if errorlevel 1 (
    call :log "Some packages may have verification issues but continuing setup..."
) else (
    call :log "Package verification successful"
)

del verify_packages.py
call :log "Package verification complete. Continuing with setup..."

:: Create data directory if it doesn't exist
if not exist data mkdir data

:: Download scripts from GitHub
call :log "Downloading scripts from GitHub..."

:: Set GitHub repository URL and branch
set GITHUB_REPO=https://raw.githubusercontent.com/inimical023/rc_zoho/main

:: Download all necessary files with improved error handling
call :download_file "common.py" "%GITHUB_REPO%/common.py"
call :download_file "accepted_calls.py" "%GITHUB_REPO%/accepted_calls.py"
call :download_file "missed_calls.py" "%GITHUB_REPO%/missed_calls.py"
call :download_file "secure_credentials.py" "%GITHUB_REPO%/secure_credentials.py"
call :download_file "unified_admin.py" "%GITHUB_REPO%/unified_admin.py"
call :download_file "requirements.txt" "%GITHUB_REPO%/requirements.txt"
call :download_file "README.md" "%GITHUB_REPO%/README.md"

:: Verify that essential files were downloaded
call :log "Verifying file downloads..."
set missing_files=0
for %%f in (common.py unified_admin.py secure_credentials.py) do (
    if not exist %%f (
        call :log "ERROR: Essential file %%f is missing!"
        set /a missing_files+=1
    )
)

if %missing_files% GTR 0 (
    call :log "ERROR: %missing_files% essential files are missing. Setup cannot continue."
    pause
    exit /b 1
)

:: Create launch_admin.bat
call :log "Creating launch_admin.bat..."
(
    echo @echo off
    echo call .venv\Scripts\activate.bat
    echo python unified_admin.py %%*
) > launch_admin.bat

:: Verify launch_admin.bat was created
if not exist launch_admin.bat (
    call :log "ERROR: Failed to create launch_admin.bat"
    pause
    exit /b 1
)

:: Create other launcher scripts
call :log "Creating launcher scripts..."
(
    echo @echo off
    echo call .venv\Scripts\activate.bat
    echo python setup_credentials.py %%*
) > run_setup_credentials.bat

(
    echo @echo off
    echo call .venv\Scripts\activate.bat
    echo python accepted_calls.py %%*
) > run_accepted_calls.bat

(
    echo @echo off
    echo call .venv\Scripts\activate.bat
    echo python missed_calls.py %%*
) > run_missed_calls.bat

call :log ""
call :log "=========================================================="
call :log "  Setup Complete!"
call :log "=========================================================="
call :log ""
call :log "The integration environment has been set up."
call :log ""
call :log "Next steps:"
call :log "1. Configure your API credentials using:"
call :log "   run_setup_credentials.bat"
call :log ""
call :log "2. Run the unified admin interface:"
call :log "   launch_admin.bat"
call :log ""
call :log "Log file location: %log_file%"
call :log ""

:: Create a simple setup_credentials.py if it doesn't exist
if not exist setup_credentials.py (
    call :log "Creating basic setup_credentials.py..."
    echo import os > setup_credentials.py
    echo import sys >> setup_credentials.py
    echo import logging >> setup_credentials.py
    echo from pathlib import Path >> setup_credentials.py
    echo. >> setup_credentials.py
    echo # Configure logging >> setup_credentials.py
    echo logging.basicConfig( >> setup_credentials.py
    echo     level=logging.INFO, >> setup_credentials.py
    echo     format='%%(asctime)s - %%(levelname)s - %%(message)s', >> setup_credentials.py
    echo     handlers=[ >> setup_credentials.py
    echo         logging.FileHandler('logs/setup_credentials.log'), >> setup_credentials.py
    echo         logging.StreamHandler() >> setup_credentials.py
    echo     ] >> setup_credentials.py
    echo ) >> setup_credentials.py
    echo. >> setup_credentials.py
    echo def main(): >> setup_credentials.py
    echo     """Main function""" >> setup_credentials.py
    echo     print("Setting up credentials...") >> setup_credentials.py
    echo     print("Please check the documentation for details on how to obtain API credentials.") >> setup_credentials.py
    echo. >> setup_credentials.py
    echo if __name__ == "__main__": >> setup_credentials.py
    echo     main() >> setup_credentials.py
)

:: End of script
call :log "Setup completed with exit code 0 (success)"
exit /b 0 