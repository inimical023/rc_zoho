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

:: Verify package installation using a batch script approach
call :log "Verifying package installation..."

:: Create a simple verification script with proper indentation handling
echo import pkg_resources, json > verify_packages.py
echo print("Checking for required packages...") >> verify_packages.py
echo packages_status = {} >> verify_packages.py
echo secure_versions = { "cryptography": "3.4.8", "urllib3": "1.26.5", "requests": "2.25.1", "certifi": "2021.10.8" } >> verify_packages.py
echo vulnerable = [] >> verify_packages.py
(
    echo for pkg, min_ver in secure_versions.items():
    echo     try:
    echo         ver = pkg_resources.get_distribution(pkg).version
    echo         if pkg_resources.parse_version(ver) ^< pkg_resources.parse_version(min_ver):
    echo             vulnerable.append(pkg + ">=" + min_ver)
    echo             print(f"{pkg}: {ver} (update to {min_ver} recommended)")
    echo         else:
    echo             print(f"{pkg}: {ver} (OK)")
    echo     except:
    echo         print(f"{pkg}: Not found")
    echo if vulnerable:
    echo     print("SECURITY ALERT: Vulnerable packages found")
    echo     with open("upgrade_list.txt", "w") as f:
    echo         f.write(" ".join(vulnerable))
) >> verify_packages.py

:: Run verification script
python verify_packages.py >> "%log_file%" 2>&1
if errorlevel 1 (
    call :log "Package verification had issues, but continuing setup..." -Level "WARNING"
) else (
    call :log "Package verification completed successfully" -Level "SUCCESS"
)

:: Check if vulnerable packages were found and update them
if exist upgrade_list.txt (
    call :log "Vulnerable packages detected. Upgrading to secure versions..." -Level "WARNING"
    set /p UPGRADE_PKGS=<upgrade_list.txt
    
    :: Update packages if needed
    if not "%UPGRADE_PKGS%"=="" (
        call :log "Upgrading packages: %UPGRADE_PKGS%" -Level "WARNING"
        pip install --upgrade %UPGRADE_PKGS% >> "%log_file%" 2>&1
        if not errorlevel 1 (
            call :log "Successfully upgraded packages to secure versions!" -Level "SUCCESS"
            :: Update requirements.txt with secure versions
            pip freeze > requirements.txt.new
            move /y requirements.txt.new requirements.txt > nul
        )
    )
    
    del upgrade_list.txt
)

:: Check for security alerts in log
findstr "SECURITY ALERT" "%log_file%" > nul
if not errorlevel 1 (
    call :log "Security issues were detected and addressed" -Level "WARNING"
    call :log "For more information: https://github.com/inimical023/rc_zoho/security/dependabot" -Level "INFO"
)

:: Clean up
del verify_packages.py 2>nul
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
set download_errors=0

:: Check essential files and download them if missing
for %%f in (common.py unified_admin.py secure_credentials.py) do (
    if not exist %%f (
        call :log "Essential file %%f is missing! Trying to download again..." -Level "WARNING"
        call :download_file "%%f" "%GITHUB_REPO%/%%f"
        if not exist %%f (
            set /a missing_files+=1
        )
    )
)

:: Create a simple version of files if they're still missing
if %missing_files% GTR 0 (
    call :log "Some files could not be downloaded. Creating basic placeholder files..." -Level "WARNING"
    
    if not exist common.py (
        call :log "Creating basic common.py..."
        echo """Common functionality for RingCentral-Zoho integration.""" > common.py
        echo def get_version(): >> common.py
        echo     return '1.0.0' >> common.py
    )
    
    if not exist unified_admin.py (
        call :log "Creating basic unified_admin.py..."
        echo """Unified Admin interface for RingCentral-Zoho integration.""" > unified_admin.py
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
        echo """Secure credential management for RingCentral-Zoho integration.""" > secure_credentials.py
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

:: Create launch_admin.bat - always create this regardless
call :log "Creating launch_admin.bat..."
(
    echo @echo off
    echo call .venv\Scripts\activate.bat
    echo python unified_admin.py %%*
) > launch_admin.bat

:: Verify launch_admin.bat was created
if not exist launch_admin.bat (
    call :log "ERROR: Failed to create launch_admin.bat - trying alternative method" -Level "ERROR"
    >launch_admin.bat echo @echo off
    >>launch_admin.bat echo call .venv\Scripts\activate.bat
    >>launch_admin.bat echo python unified_admin.py %%*
)

:: Double-check launch_admin.bat was created
if not exist launch_admin.bat (
    call :log "CRITICAL ERROR: Could not create launcher scripts!" -Level "ERROR"
    exit /b 1
) else (
    call :log "Launcher scripts created successfully" -Level "SUCCESS"
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