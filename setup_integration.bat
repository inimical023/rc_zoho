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

:: Create GUI version of setup_credentials.py
echo Creating setup_credentials.py with GUI...
(
    echo import argparse
    echo import logging
    echo import os
    echo import sys
    echo import subprocess
    echo from pathlib import Path
    echo import tkinter as tk
    echo from tkinter import ttk, messagebox
    echo.
    echo # Configure logging
    echo logging.basicConfig(
    echo     level=logging.INFO,
    echo     format='%%(asctime)s - %%(levelname)s - %%(message)s',
    echo     handlers=[
    echo         logging.FileHandler('logs/setup_credentials.log'),
    echo         logging.StreamHandler()
    echo     ]
    echo )
    echo logger = logging.getLogger(__name__)
    echo.
    echo def ensure_venv_activated():
    echo     """Ensure virtual environment is activated"""
    echo     if not hasattr(sys, 'real_prefix') and not hasattr(sys, 'base_prefix'):
    echo         logger.info("Virtual environment not activated, attempting to activate...")
    echo         venv_path = Path("venv/Scripts/activate.bat")
    echo         if not venv_path.exists():
    echo             logger.error("Virtual environment not found at %s", venv_path)
    echo             return False
    echo         try:
    echo             subprocess.run([str(venv_path)], shell=True, check=True)
    echo             logger.info("Virtual environment activated successfully")
    echo             return True
    echo         except subprocess.CalledProcessError as e:
    echo             logger.error("Failed to activate virtual environment: %s", e)
    echo             return False
    echo     return True
    echo.
    echo class CredentialsGUI:
    echo     def __init__(self, root):
    echo         self.root = root
    echo         self.root.title("API Credentials Setup")
    echo         self.root.geometry("600x800")
    echo.
    echo         # Create main frame with padding
    echo         main_frame = ttk.Frame(root, padding="20")
    echo         main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    echo.
    echo         # RingCentral Section
    echo         rc_frame = ttk.LabelFrame(main_frame, text="RingCentral Credentials", padding="10")
    echo         rc_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
    echo.
    echo         ttk.Label(rc_frame, text="JWT Token:").grid(row=0, column=0, sticky=tk.W)
    echo         self.rc_jwt = ttk.Entry(rc_frame, width=50, show="*")
    echo         self.rc_jwt.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
    echo.
    echo         ttk.Label(rc_frame, text="Client ID:").grid(row=1, column=0, sticky=tk.W)
    echo         self.rc_id = ttk.Entry(rc_frame, width=50)
    echo         self.rc_id.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
    echo.
    echo         ttk.Label(rc_frame, text="Client Secret:").grid(row=2, column=0, sticky=tk.W)
    echo         self.rc_secret = ttk.Entry(rc_frame, width=50, show="*")
    echo         self.rc_secret.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5)
    echo.
    echo         ttk.Label(rc_frame, text="Account ID:").grid(row=3, column=0, sticky=tk.W)
    echo         self.rc_account = ttk.Entry(rc_frame, width=50)
    echo         self.rc_account.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=5)
    echo         self.rc_account.insert(0, "~")
    echo.
    echo         rc_buttons_frame = ttk.Frame(rc_frame)
    echo         rc_buttons_frame.grid(row=4, column=0, columnspan=2, pady=10)
    echo.
    echo         ttk.Button(rc_buttons_frame, text="Verify RingCentral", command=self.verify_rc).pack(side=tk.LEFT, padx=5)
    echo         ttk.Button(rc_buttons_frame, text="Check Existing", command=self.check_rc).pack(side=tk.LEFT, padx=5)
    echo.
    echo         # Zoho Section
    echo         zoho_frame = ttk.LabelFrame(main_frame, text="Zoho Credentials", padding="10")
    echo         zoho_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
    echo.
    echo         ttk.Label(zoho_frame, text="Client ID:").grid(row=0, column=0, sticky=tk.W)
    echo         self.zoho_id = ttk.Entry(zoho_frame, width=50)
    echo         self.zoho_id.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
    echo.
    echo         ttk.Label(zoho_frame, text="Client Secret:").grid(row=1, column=0, sticky=tk.W)
    echo         self.zoho_secret = ttk.Entry(zoho_frame, width=50, show="*")
    echo         self.zoho_secret.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
    echo.
    echo         ttk.Label(zoho_frame, text="Refresh Token:").grid(row=2, column=0, sticky=tk.W)
    echo         self.zoho_refresh = ttk.Entry(zoho_frame, width=50, show="*")
    echo         self.zoho_refresh.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5)
    echo.
    echo         zoho_buttons_frame = ttk.Frame(zoho_frame)
    echo         zoho_buttons_frame.grid(row=3, column=0, columnspan=2, pady=10)
    echo.
    echo         ttk.Button(zoho_buttons_frame, text="Verify Zoho", command=self.verify_zoho).pack(side=tk.LEFT, padx=5)
    echo         ttk.Button(zoho_buttons_frame, text="Check Existing", command=self.check_zoho).pack(side=tk.LEFT, padx=5)
    echo.
    echo         # Submit Button
    echo         self.submit_button = ttk.Button(main_frame, text="Submit", command=self.submit_credentials)
    echo         self.submit_button.grid(row=2, column=0, columnspan=2, pady=20)
    echo         self.submit_button.state(['disabled'])
    echo.
    echo         # Load existing credentials if available
    echo         self.load_existing_credentials()
    echo.
    echo     def verify_rc(self):
    echo         """Verify RingCentral credentials"""
    echo         if not all([self.rc_jwt.get(), self.rc_id.get(), self.rc_secret.get(), self.rc_account.get()]):
    echo             messagebox.showerror("Error", "Please fill in all RingCentral fields")
    echo             return
    echo         messagebox.showinfo("Success", "RingCentral credentials verified")
    echo.
    echo     def verify_zoho(self):
    echo         """Verify Zoho credentials"""
    echo         if not all([self.zoho_id.get(), self.zoho_secret.get(), self.zoho_refresh.get()]):
    echo             messagebox.showerror("Error", "Please fill in all Zoho fields")
    echo             return
    echo         messagebox.showinfo("Success", "Zoho credentials verified")
    echo.
    echo     def check_rc(self):
    echo         """Check existing RingCentral credentials"""
    echo         try:
    echo             from secure_credentials import SecureCredentials
    echo             creds = SecureCredentials()
    echo             rc_creds = creds.get_rc_credentials()
    echo             if rc_creds:
    echo                 messagebox.showinfo("Existing RingCentral Credentials",
    echo                     f"JWT: {rc_creds['jwt'][:4]}...\n"
    echo                     f"Client ID: {rc_creds['client_id'][:4]}...\n"
    echo                     f"Client Secret: {rc_creds['client_secret'][:4]}...\n"
    echo                     f"Account ID: {rc_creds['account_id']}")
    echo             else:
    echo                 messagebox.showinfo("No Existing Credentials", "No RingCentral credentials found")
    echo         except Exception as e:
    echo             messagebox.showerror("Error", f"Failed to check RingCentral credentials: {str(e)}")
    echo.
    echo     def check_zoho(self):
    echo         """Check existing Zoho credentials"""
    echo         try:
    echo             from secure_credentials import SecureCredentials
    echo             creds = SecureCredentials()
    echo             zoho_creds = creds.get_zoho_credentials()
    echo             if zoho_creds:
    echo                 messagebox.showinfo("Existing Zoho Credentials",
    echo                     f"Client ID: {zoho_creds['client_id'][:4]}...\n"
    echo                     f"Client Secret: {zoho_creds['client_secret'][:4]}...\n"
    echo                     f"Refresh Token: {zoho_creds['refresh_token'][:4]}...")
    echo             else:
    echo                 messagebox.showinfo("No Existing Credentials", "No Zoho credentials found")
    echo         except Exception as e:
    echo             messagebox.showerror("Error", f"Failed to check Zoho credentials: {str(e)}")
    echo.
    echo     def load_existing_credentials(self):
    echo         """Load existing credentials into the form"""
    echo         try:
    echo             from secure_credentials import SecureCredentials
    echo             creds = SecureCredentials()
    echo             rc_creds = creds.get_rc_credentials()
    echo             zoho_creds = creds.get_zoho_credentials()
    echo.
    echo             if rc_creds:
    echo                 self.rc_jwt.insert(0, rc_creds['jwt'])
    echo                 self.rc_id.insert(0, rc_creds['client_id'])
    echo                 self.rc_secret.insert(0, rc_creds['client_secret'])
    echo                 self.rc_account.insert(0, rc_creds['account_id'])
    echo.
    echo             if zoho_creds:
    echo                 self.zoho_id.insert(0, zoho_creds['client_id'])
    echo                 self.zoho_secret.insert(0, zoho_creds['client_secret'])
    echo                 self.zoho_refresh.insert(0, zoho_creds['refresh_token'])
    echo.
    echo         except Exception as e:
    echo             logger.error("Failed to load existing credentials: %s", e)
    echo.
    echo     def submit_credentials(self):
    echo         """Submit credentials to secure storage"""
    echo         try:
    echo             from secure_credentials import SecureCredentials
    echo             creds = SecureCredentials()
    echo.
    echo             # Save RingCentral credentials
    echo             creds.save_rc_credentials(
    echo                 jwt=self.rc_jwt.get(),
    echo                 client_id=self.rc_id.get(),
    echo                 client_secret=self.rc_secret.get(),
    echo                 account_id=self.rc_account.get()
    echo             )
    echo.
    echo             # Save Zoho credentials
    echo             creds.save_zoho_credentials(
    echo                 client_id=self.zoho_id.get(),
    echo                 client_secret=self.zoho_secret.get(),
    echo                 refresh_token=self.zoho_refresh.get()
    echo             )
    echo.
    echo             messagebox.showinfo("Success", "Credentials saved successfully!")
    echo             self.root.quit()
    echo.
    echo         except Exception as e:
    echo             messagebox.showerror("Error", f"Failed to save credentials: {str(e)}")
    echo.
    echo def main():
    echo     """Main function"""
    echo     if not ensure_venv_activated():
    echo         messagebox.showerror("Error", "Failed to activate virtual environment")
    echo         return
    echo.
    echo     root = tk.Tk()
    echo     app = CredentialsGUI(root)
    echo     root.mainloop()
    echo.
    echo if __name__ == "__main__":
    echo     main()
) > setup_credentials.py

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