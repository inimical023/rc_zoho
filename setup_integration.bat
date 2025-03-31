@echo off
setlocal enabledelayedexpansion

echo ==========================================================
echo  RingCentral-Zoho Integration Setup
echo ==========================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed. Please install Python 3.8 or later.
    pause
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: Activate virtual environment
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo Failed to activate virtual environment.
    pause
    exit /b 1
)

:: Install required packages
echo Installing required packages...
python -m pip install --upgrade pip
pip install --upgrade requests cryptography python-dateutil pytz urllib3 certifi charset-normalizer idna pywin32 ringcentral python-dotenv

:: Verify package installation
echo Verifying package installation...
python -c "import cryptography; import dotenv; import requests; import dateutil; import pytz; import urllib3; import certifi; import charset_normalizer; import idna; import win32api; import ringcentral; import tkinter; print('All required packages installed successfully!')"
if errorlevel 1 (
    echo Failed to install required packages.
    pause
    exit /b 1
)

:: Create data directory if it doesn't exist
if not exist data mkdir data

:: Create extensions.txt with the provided extensions
echo Creating extensions.txt...
(
    echo 1263971040
    echo 1338124040
    echo 1338137040
    echo 737929040
    echo 859647040
) > data\extensions.txt

:: Download scripts from GitHub
echo Downloading scripts from GitHub...

:: Set GitHub repository URL and branch
set GITHUB_REPO=https://raw.githubusercontent.com/inimical023/rc_zoho/main

:: Download common.py
echo Downloading common.py...
curl -o common.py "%GITHUB_REPO%/common.py"
if errorlevel 1 (
    echo Failed to download common.py
    pause
    exit /b 1
)

:: Download accepted_calls.py
echo Downloading accepted_calls.py...
curl -o accepted_calls.py "%GITHUB_REPO%/accepted_calls.py"
if errorlevel 1 (
    echo Failed to download accepted_calls.py
    pause
    exit /b 1
)

:: Download missed_calls.py
echo Downloading missed_calls.py...
curl -o missed_calls.py "%GITHUB_REPO%/missed_calls.py"
if errorlevel 1 (
    echo Failed to download missed_calls.py
    pause
    exit /b 1
)

:: Download secure_credentials.py
echo Downloading secure_credentials.py...
curl -o secure_credentials.py "%GITHUB_REPO%/secure_credentials.py"
if errorlevel 1 (
    echo Failed to download secure_credentials.py
    pause
    exit /b 1
)

:: Download setup_credentials.py
echo Downloading setup_credentials.py...
curl -o setup_credentials.py "%GITHUB_REPO%/setup_credentials.py"
if errorlevel 1 (
    echo Failed to download setup_credentials.py
    pause
    exit /b 1
)

:: Create logs directory if it doesn't exist
if not exist logs mkdir logs

:: Create launcher scripts
echo Creating launcher scripts...
(
    echo @echo off
    echo call venv\Scripts\activate.bat
    echo python setup_credentials.py %%*
) > run_setup_credentials.bat

(
    echo @echo off
    echo call venv\Scripts\activate.bat
    echo python accepted_calls.py %%*
) > run_accepted_calls.bat

(
    echo @echo off
    echo call venv\Scripts\activate.bat
    echo python missed_calls.py %%*
) > run_missed_calls.bat

echo.
echo ==========================================================
echo  Setup Complete!
echo ==========================================================
echo.
echo The integration environment has been set up.
echo.
echo Next steps:
echo 1. Run setup_credentials.py to securely store your API credentials:
echo    run_setup_credentials.bat --rc-jwt "your_rc_jwt" --rc-id "your_rc_id" --rc-secret "your_rc_secret" --rc-account "~" --zoho-id "your_zoho_id" --zoho-secret "your_zoho_secret" --zoho-refresh "your_zoho_refresh"
echo.
echo 2. Once credentials are set up, you can run the scripts:
echo    For accepted calls:
echo    run_accepted_calls.bat [--debug] [--dry-run]
echo.
echo    For missed calls:
echo    run_missed_calls.bat [--debug] [--dry-run]
echo.
pause 