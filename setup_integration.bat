@echo off
setlocal enabledelayedexpansion

:: Create logs directory if it doesn't exist
if not exist logs mkdir logs

:: Set up logging
set "log_file=logs\setup_integration_%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%.log"

:: Python installation variables
set "PYTHON_VERSION=3.8.10"
set "PYTHON_URL=https://www.python.org/ftp/python/3.8.10/python-3.8.10-amd64.exe"
set "PYTHON_INSTALLER=%TEMP%\python-installer.exe"
set "PYTHON_PATH=%LOCALAPPDATA%\Programs\Python\Python38"
set "PYTHON_SCRIPTS=%LOCALAPPDATA%\Programs\Python\Python38\Scripts"

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

:check_python
where python >nul 2>&1
if errorlevel 1 (
    call :log "Python not found in PATH"
    exit /b 1
)

python --version 2>nul | findstr /r "3\.[8-9]\|3\.1[0-9]" >nul
if errorlevel 1 (
    call :log "Python 3.8 or higher not found"
    exit /b 1
)

call :log "Python 3.8+ found"
exit /b 0

:install_python
call :log "Downloading Python %PYTHON_VERSION% installer..."
powershell -Command "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%'" >> "%log_file%" 2>&1
if errorlevel 1 (
    call :log "Failed to download Python installer"
    exit /b 1
)

call :log "Installing Python %PYTHON_VERSION%..."
call :log "This may take a few minutes..."
"%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0 Include_doc=0 TargetDir="%PYTHON_PATH%" >> "%log_file%" 2>&1
if errorlevel 1 (
    call :log "Python installation failed"
    exit /b 1
)

call :log "Python installed successfully. Refreshing environment variables..."
:: Refresh PATH environment variable
for /f "tokens=2*" %%a in ('reg query HKCU\Environment /v PATH') do set "USER_PATH=%%b"
setx PATH "%PYTHON_PATH%;%PYTHON_PATH%\Scripts;%USER_PATH%" >nul

:: Update current session PATH
set "PATH=%PYTHON_PATH%;%PYTHON_PATH%\Scripts;%PATH%"

call :log "Environment variables updated"
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
call :log "Checking for Python installation..."
call :check_python
if errorlevel 1 (
    call :log "Python 3.8 or higher is required but not found."
    call :log "Automatically installing Python 3.8..."
    call :install_python
    if errorlevel 1 (
        call :log "Failed to install Python. Please install manually from https://www.python.org/downloads/"
        call :log "IMPORTANT: Check 'Add Python to PATH' during installation"
        pause
        exit /b 1
    )
    
    :: IMPORTANT: Force the PATH to include Python path explicitly
    set "PATH=%PYTHON_PATH%;%PYTHON_PATH%\Scripts;%PATH%"
    call :log "Explicitly added Python to PATH: %PYTHON_PATH%"
    
    call :log "Verifying Python installation..."
    call :check_python
    if errorlevel 1 (
        call :log "Python was installed but could not be found in PATH."
        call :log "Attempting to use full path to Python..."
        set "PYTHON_EXE=%PYTHON_PATH%\python.exe"
        call :log "Using Python at: %PYTHON_EXE%"
    ) else (
        call :log "Python installation successful!"
        set "PYTHON_EXE=python"
    )
) else (
    call :log "Python is properly installed."
    set "PYTHON_EXE=python"
)

call :log "Continuing setup with Python: %PYTHON_EXE%"

:: Create virtual environment if it doesn't exist
if not exist .venv (
    call :log "Creating virtual environment..."
    "%PYTHON_EXE%" -m venv .venv >> "%log_file%" 2>&1
    if errorlevel 1 (
        call :log "Failed to create virtual environment."
        call :log "Attempting with explicit path to venv module..."
        "%PYTHON_EXE%" -m venv --help >> "%log_file%" 2>&1
        "%PYTHON_EXE%" -m venv .venv >> "%log_file%" 2>&1
        if errorlevel 1 (
            call :log "Failed to create virtual environment after retry."
            pause
            exit /b 1
        )
    )
)

:: Activate virtual environment
call :log "Activating virtual environment..."
call .venv\Scripts\activate.bat
if errorlevel 1 (
    call :log "Failed to activate virtual environment."
    call :log "Attempting to install requirements directly with system Python..."
    set "USE_SYSTEM_PYTHON=1"
) else (
    set "USE_SYSTEM_PYTHON=0"
)

:: Install required packages
call :log "Installing required packages..."
if "%USE_SYSTEM_PYTHON%"=="1" (
    "%PYTHON_EXE%" -m pip install --upgrade pip >> "%log_file%" 2>&1
    "%PYTHON_EXE%" -m pip install "setuptools>=40.0.0" >> "%log_file%" 2>&1
    "%PYTHON_EXE%" -m pip install "tkcalendar>=1.6.0" >> "%log_file%" 2>&1
) else (
    python -m pip install --upgrade pip >> "%log_file%" 2>&1
    python -m pip install "setuptools>=40.0.0" >> "%log_file%" 2>&1
    python -m pip install "tkcalendar>=1.6.0" >> "%log_file%" 2>&1
)

:: Check if requirements.txt exists
if exist requirements.txt (
    call :log "Found requirements.txt, installing dependencies..."
    if "%USE_SYSTEM_PYTHON%"=="1" (
        "%PYTHON_EXE%" -m pip install -r requirements.txt >> "%log_file%" 2>&1
    ) else (
        pip install -r requirements.txt >> "%log_file%" 2>&1
    )
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
    echo ttkbootstrap>=1.10.1 >> requirements.txt
    echo pillow>=9.0.0 >> requirements.txt
    if "%USE_SYSTEM_PYTHON%"=="1" (
        "%PYTHON_EXE%" -m pip install -r requirements.txt >> "%log_file%" 2>&1
    ) else (
        pip install -r requirements.txt >> "%log_file%" 2>&1
    )
)

:: Create launcher scripts immediately to ensure they exist even if later steps fail
call :log "Creating launcher scripts (early creation for resilience)..."

:: Create launch_admin.bat - critical file for PowerShell detection
call :log "Creating launch_admin.bat..."
(
    echo @echo off
    if "%USE_SYSTEM_PYTHON%"=="1" (
        echo set "PATH=%PYTHON_PATH%;%PYTHON_PATH%\Scripts;%%PATH%%"
        echo "%PYTHON_EXE%" unified_admin.py %%*
    ) else (
        echo call .venv\Scripts\activate.bat
        echo python unified_admin.py %%*
    )
) > launch_admin.bat

:: Check if this critical file was created
if not exist launch_admin.bat (
    call :log "ERROR: Failed initial creation of launch_admin.bat - trying alternative method" -Level "ERROR"
    >launch_admin.bat echo @echo off
    if "%USE_SYSTEM_PYTHON%"=="1" (
        >>launch_admin.bat echo set "PATH=%PYTHON_PATH%;%PYTHON_PATH%\Scripts;%%PATH%%"
        >>launch_admin.bat echo "%PYTHON_EXE%" unified_admin.py %%*
    ) else (
        >>launch_admin.bat echo call .venv\Scripts\activate.bat
        >>launch_admin.bat echo python unified_admin.py %%*
    )
)

:: Create other launcher scripts with system Python fallback
(
    echo @echo off
    if "%USE_SYSTEM_PYTHON%"=="1" (
        echo set "PATH=%PYTHON_PATH%;%PYTHON_PATH%\Scripts;%%PATH%%"
        echo "%PYTHON_EXE%" setup_credentials.py %%*
    ) else (
        echo call .venv\Scripts\activate.bat
        echo python setup_credentials.py %%*
    )
) > run_setup_credentials.bat

(
    echo @echo off
    if "%USE_SYSTEM_PYTHON%"=="1" (
        echo set "PATH=%PYTHON_PATH%;%PYTHON_PATH%\Scripts;%%PATH%%"
        echo "%PYTHON_EXE%" accepted_calls.py %%*
    ) else (
        echo call .venv\Scripts\activate.bat
        echo python accepted_calls.py %%*
    )
) > run_accepted_calls.bat

(
    echo @echo off
    if "%USE_SYSTEM_PYTHON%"=="1" (
        echo set "PATH=%PYTHON_PATH%;%PYTHON_PATH%\Scripts;%%PATH%%"
        echo "%PYTHON_EXE%" missed_calls.py %%*
    ) else (
        echo call .venv\Scripts\activate.bat
        echo python missed_calls.py %%*
    )
) > run_missed_calls.bat

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
call :download_file "setup_credentials.py" "%GITHUB_REPO%/setup_credentials.py"
call :download_file "unified_admin.py" "%GITHUB_REPO%/unified_admin.py"
call :download_file "requirements.txt" "%GITHUB_REPO%/requirements.txt"
call :download_file "README.md" "%GITHUB_REPO%/README.md"

:: Verify that essential files were downloaded
call :log "Verifying file downloads..."
set missing_files=0
set download_errors=0

:: Check essential files and download them if missing
for %%f in (common.py unified_admin.py secure_credentials.py setup_credentials.py) do (
    if not exist %%f (
        call :log "Essential file %%f is missing! Trying to download again..."
        call :download_file "%%f" "%GITHUB_REPO%/%%f"
        if not exist %%f (
            set /a missing_files+=1
        )
    )
)

:: Create a simple version of files if they're still missing
if %missing_files% GTR 0 (
    call :log "Some files could not be downloaded. Creating basic placeholder files..."
    
    if not exist common.py (
        call :log "Creating basic common.py..."
        echo # Common functionality for RingCentral-Zoho integration > common.py
        echo def get_version(): >> common.py
        echo     return '1.0.0' >> common.py
    )
    
    if not exist unified_admin.py (
        call :log "Creating basic unified_admin.py..."
        echo # Unified Admin interface for RingCentral-Zoho integration > unified_admin.py
        echo import tkinter as tk >> unified_admin.py
        echo from tkinter import ttk, messagebox >> unified_admin.py
        echo. >> unified_admin.py
        echo def main(): >> unified_admin.py
        echo     root = tk.Tk() >> unified_admin.py
        echo     root.title("RingCentral-Zoho Admin") >> unified_admin.py
        echo     ttk.Label(root, text="Welcome to RingCentral-Zoho Integration").pack(pady=20) >> unified_admin.py
        echo     ttk.Label(root, text="Basic Setup: Please download the full version").pack() >> unified_admin.py
        echo     ttk.Button(root, text="Exit", command=root.destroy).pack(pady=10) >> unified_admin.py
        echo     root.mainloop() >> unified_admin.py
        echo. >> unified_admin.py
        echo if __name__ == "__main__": >> unified_admin.py
        echo     main() >> unified_admin.py
    )
    
    if not exist secure_credentials.py (
        call :log "Creating basic secure_credentials.py..."
        echo # Secure credential management for RingCentral-Zoho integration > secure_credentials.py
        echo class SecureCredentials: >> secure_credentials.py
        echo     def __init__(self): >> secure_credentials.py
        echo         self.rc_creds = None >> secure_credentials.py
        echo         self.zoho_creds = None >> secure_credentials.py
        echo. >> secure_credentials.py
        echo     def get_rc_credentials(self): >> secure_credentials.py
        echo         return self.rc_creds >> secure_credentials.py
        echo. >> secure_credentials.py
        echo     def get_zoho_credentials(self): >> secure_credentials.py
        echo         return self.zoho_creds >> secure_credentials.py
    )
)

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

:: Create setup_credentials.py if it doesn't exist
if not exist setup_credentials.py (
    call :log "Creating basic setup_credentials.py as download failed..."
    
    (
        echo import os
        echo import sys
        echo import logging
        echo from pathlib import Path
        echo.
        echo # Configure logging
        echo logging.basicConfig(
        echo     level=logging.INFO,
        echo     format='%%(asctime)s - %%(levelname)s - %%(message)s',
        echo     handlers=[
        echo         logging.FileHandler('logs/setup_credentials.log'^),
        echo         logging.StreamHandler(^)
        echo     ]
        echo ^)
        echo.
        echo def main(^):
        echo     """Main function"""
        echo     print("Setting up credentials..."^)
        echo     print("Please check the documentation for details on how to obtain API credentials."^)
        echo     print("IMPORTANT: This is a placeholder file created during installation."^)
        echo     print("The full version should have been downloaded from GitHub."^)
        echo     print("Please re-run the installer or download the file manually."^)
        echo.
        echo if __name__ == "__main__":
        echo     main(^)
    ) > setup_credentials.py
)

:: End of script
call :log "Setup completed with exit code 0 (success)"
exit /b 0 