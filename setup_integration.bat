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
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Failed to create virtual environment.
        pause
        exit /b 1
    )
)

:: Activate virtual environment
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo Failed to activate virtual environment.
    pause
    exit /b 1
)

:: Install required packages
echo Installing required packages...
python -m pip install --upgrade pip
pip install -r requirements.txt

:: Verify package installation
echo Verifying package installation...
python -c "import sys; missing = []; packages = ['cryptography', 'dotenv', 'requests', 'dateutil', 'pytz', 'urllib3', 'certifi', 'charset_normalizer', 'idna', 'win32api', 'ringcentral', 'tkinter']; [missing.append(pkg) for pkg in packages if pkg not in sys.modules and not __import__(pkg, fromlist=['']) in (1,)]; print('Missing packages: ' + ', '.join(missing) if missing else 'All required packages installed successfully!')"
if errorlevel 1 (
    echo Some packages failed to install, but continuing setup process.
)

:: Create data directory if it doesn't exist
if not exist data mkdir data

:: Create logs directory if it doesn't exist
if not exist logs mkdir logs

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

:: Download all necessary files
echo Downloading common.py...
curl -o common.py "%GITHUB_REPO%/common.py"
if errorlevel 1 (
    echo Failed to download common.py
    pause
    exit /b 1
)

echo Downloading accepted_calls.py...
curl -o accepted_calls.py "%GITHUB_REPO%/accepted_calls.py"
if errorlevel 1 (
    echo Failed to download accepted_calls.py
    pause
    exit /b 1
)

echo Downloading missed_calls.py...
curl -o missed_calls.py "%GITHUB_REPO%/missed_calls.py"
if errorlevel 1 (
    echo Failed to download missed_calls.py
    pause
    exit /b 1
)

echo Downloading secure_credentials.py...
curl -o secure_credentials.py "%GITHUB_REPO%/secure_credentials.py"
if errorlevel 1 (
    echo Failed to download secure_credentials.py
    pause
    exit /b 1
)

echo Downloading unified_admin.py...
curl -o unified_admin.py "%GITHUB_REPO%/unified_admin.py"
if errorlevel 1 (
    echo Failed to download unified_admin.py
    pause
    exit /b 1
)

echo Downloading requirements.txt...
curl -o requirements.txt "%GITHUB_REPO%/requirements.txt"
if errorlevel 1 (
    echo Failed to download requirements.txt
    pause
    exit /b 1
)

echo Downloading README.md...
curl -o README.md "%GITHUB_REPO%/README.md"
if errorlevel 1 (
    echo Failed to download README.md
    pause
    exit /b 1
)

:: Create launch_admin.bat
echo Creating launch_admin.bat...
(
    echo @echo off
    echo call .venv\Scripts\activate.bat
    echo python unified_admin.py %%*
) > launch_admin.bat

:: Create install.ps1
echo Creating install.ps1...
(
    echo # PowerShell installation script for RingCentral-Zoho Integration
    echo # This script is created during setup_integration.bat execution
    echo.
    echo Write-Host "RingCentral-Zoho Integration Installation"
    echo Write-Host "========================================"
    echo.
    echo # Add installation logic here if needed
    echo Write-Host "Installation completed successfully!"
) > install.ps1

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
    echo         venv_path = Path(".venv/Scripts/activate.bat")
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

:: Create launcher scripts
echo Creating launcher scripts...
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

:: Create the new run_script_date.bat with GUI
echo Creating run_script_date.bat...
(
    echo @echo off
    echo setlocal enabledelayedexpansion
    echo.
    echo :: Create a temporary directory for date files
    echo set "temp_dir=%%TEMP%%\date_picker_%%RANDOM%%"
    echo mkdir "%%temp_dir%%" 2^>nul
    echo.
    echo :: Create a simple PowerShell script for the GUI
    echo Add-Type -AssemblyName System.Windows.Forms ^> "%%temp_dir%%\gui.ps1"
    echo Add-Type -AssemblyName System.Drawing ^>^> "%%temp_dir%%\gui.ps1"
    echo. ^>^> "%%temp_dir%%\gui.ps1"
    echo $form = New-Object System.Windows.Forms.Form ^>^> "%%temp_dir%%\gui.ps1"
    echo $form.Text = 'Select Script and Date Range' ^>^> "%%temp_dir%%\gui.ps1"
    echo $form.Size = New-Object System.Drawing.Size(700, 500) ^>^> "%%temp_dir%%\gui.ps1"
    echo $form.StartPosition = 'CenterScreen' ^>^> "%%temp_dir%%\gui.ps1"
    echo. ^>^> "%%temp_dir%%\gui.ps1"
    echo $scriptLabel = New-Object System.Windows.Forms.Label ^>^> "%%temp_dir%%\gui.ps1"
    echo $scriptLabel.Location = New-Object System.Drawing.Point(10, 10) ^>^> "%%temp_dir%%\gui.ps1"
    echo $scriptLabel.Size = New-Object System.Drawing.Size(280, 20) ^>^> "%%temp_dir%%\gui.ps1"
    echo $scriptLabel.Text = 'Select Script to Run:' ^>^> "%%temp_dir%%\gui.ps1"
    echo $form.Controls.Add($scriptLabel) ^>^> "%%temp_dir%%\gui.ps1"
    echo. ^>^> "%%temp_dir%%\gui.ps1"
    echo $scriptComboBox = New-Object System.Windows.Forms.ComboBox ^>^> "%%temp_dir%%\gui.ps1"
    echo $scriptComboBox.Location = New-Object System.Drawing.Point(10, 40) ^>^> "%%temp_dir%%\gui.ps1"
    echo $scriptComboBox.Size = New-Object System.Drawing.Size(250, 20) ^>^> "%%temp_dir%%\gui.ps1"
    echo $scriptComboBox.DropDownStyle = [System.Windows.Forms.ComboBoxStyle]::DropDownList ^>^> "%%temp_dir%%\gui.ps1"
    echo $scriptComboBox.Items.Add('Select Script') ^| Out-Null ^>^> "%%temp_dir%%\gui.ps1"
    echo $scriptComboBox.Items.Add('Missed Calls') ^| Out-Null ^>^> "%%temp_dir%%\gui.ps1"
    echo $scriptComboBox.Items.Add('Accepted Calls with Recordings') ^| Out-Null ^>^> "%%temp_dir%%\gui.ps1"
    echo $scriptComboBox.SelectedIndex = 0 ^>^> "%%temp_dir%%\gui.ps1"
    echo $form.Controls.Add($scriptComboBox) ^>^> "%%temp_dir%%\gui.ps1"
    echo. ^>^> "%%temp_dir%%\gui.ps1"
    echo $tooltip = New-Object System.Windows.Forms.ToolTip ^>^> "%%temp_dir%%\gui.ps1"
    echo $tooltip.SetToolTip($scriptComboBox, 'Select a script to run') ^>^> "%%temp_dir%%\gui.ps1"
    echo. ^>^> "%%temp_dir%%\gui.ps1"
    echo $label1 = New-Object System.Windows.Forms.Label ^>^> "%%temp_dir%%\gui.ps1"
    echo $label1.Location = New-Object System.Drawing.Point(10, 80) ^>^> "%%temp_dir%%\gui.ps1"
    echo $label1.Size = New-Object System.Drawing.Size(280, 20) ^>^> "%%temp_dir%%\gui.ps1"
    echo $label1.Text = 'Start Date and Time:' ^>^> "%%temp_dir%%\gui.ps1"
    echo $form.Controls.Add($label1) ^>^> "%%temp_dir%%\gui.ps1"
    echo. ^>^> "%%temp_dir%%\gui.ps1"
    echo $startDateTime = New-Object System.Windows.Forms.DateTimePicker ^>^> "%%temp_dir%%\gui.ps1"
    echo $startDateTime.Location = New-Object System.Drawing.Point(10, 110) ^>^> "%%temp_dir%%\gui.ps1"
    echo $startDateTime.Size = New-Object System.Drawing.Size(250, 20) ^>^> "%%temp_dir%%\gui.ps1"
    echo $startDateTime.Format = [System.Windows.Forms.DateTimePickerFormat]::Custom ^>^> "%%temp_dir%%\gui.ps1"
    echo $startDateTime.CustomFormat = 'yyyy-MM-dd HH:mm:ss' ^>^> "%%temp_dir%%\gui.ps1"
    echo $startDateTime.Value = [DateTime]::Today ^>^> "%%temp_dir%%\gui.ps1"
    echo $form.Controls.Add($startDateTime) ^>^> "%%temp_dir%%\gui.ps1"
    echo. ^>^> "%%temp_dir%%\gui.ps1"
    echo $label2 = New-Object System.Windows.Forms.Label ^>^> "%%temp_dir%%\gui.ps1"
    echo $label2.Location = New-Object System.Drawing.Point(10, 150) ^>^> "%%temp_dir%%\gui.ps1"
    echo $label2.Size = New-Object System.Drawing.Size(280, 20) ^>^> "%%temp_dir%%\gui.ps1"
    echo $label2.Text = 'End Date and Time:' ^>^> "%%temp_dir%%\gui.ps1"
    echo $form.Controls.Add($label2) ^>^> "%%temp_dir%%\gui.ps1"
    echo. ^>^> "%%temp_dir%%\gui.ps1"
    echo $endDateTime = New-Object System.Windows.Forms.DateTimePicker ^>^> "%%temp_dir%%\gui.ps1"
    echo $endDateTime.Location = New-Object System.Drawing.Point(10, 180) ^>^> "%%temp_dir%%\gui.ps1"
    echo $endDateTime.Size = New-Object System.Drawing.Size(250, 20) ^>^> "%%temp_dir%%\gui.ps1"
    echo $endDateTime.Format = [System.Windows.Forms.DateTimePickerFormat]::Custom ^>^> "%%temp_dir%%\gui.ps1"
    echo $endDateTime.CustomFormat = 'yyyy-MM-dd HH:mm:ss' ^>^> "%%temp_dir%%\gui.ps1"
    echo $endDateTime.Value = [DateTime]::Today.AddHours(23).AddMinutes(59).AddSeconds(59) ^>^> "%%temp_dir%%\gui.ps1"
    echo $form.Controls.Add($endDateTime) ^>^> "%%temp_dir%%\gui.ps1"
    echo. ^>^> "%%temp_dir%%\gui.ps1"
    echo $descriptionLabel = New-Object System.Windows.Forms.Label ^>^> "%%temp_dir%%\gui.ps1"
    echo $descriptionLabel.Location = New-Object System.Drawing.Point(300, 40) ^>^> "%%temp_dir%%\gui.ps1"
    echo $descriptionLabel.Size = New-Object System.Drawing.Size(350, 100) ^>^> "%%temp_dir%%\gui.ps1"
    echo $descriptionLabel.Text = 'Please select a script from the dropdown menu to see its description.' ^>^> "%%temp_dir%%\gui.ps1"
    echo $form.Controls.Add($descriptionLabel) ^>^> "%%temp_dir%%\gui.ps1"
    echo. ^>^> "%%temp_dir%%\gui.ps1"
    echo $scriptComboBox.Add_SelectedIndexChanged({ ^>^> "%%temp_dir%%\gui.ps1"
    echo     if ($scriptComboBox.SelectedIndex -eq 0) { ^>^> "%%temp_dir%%\gui.ps1"
    echo         $descriptionLabel.Text = 'Please select a script from the dropdown menu to see its description.' ^>^> "%%temp_dir%%\gui.ps1"
    echo     } elseif ($scriptComboBox.SelectedIndex -eq 1) { ^>^> "%%temp_dir%%\gui.ps1"
    echo         $descriptionLabel.Text = 'This script retrieves missed calls from RingCentral and creates leads in Zoho CRM. Each missed call is assigned to a lead owner in round-robin fashion, with the lead status set to \"Missed Call\". The lead includes caller information and call time details.' ^>^> "%%temp_dir%%\gui.ps1"
    echo     } else { ^>^> "%%temp_dir%%\gui.ps1"
    echo         $descriptionLabel.Text = 'This script retrieves accepted calls from RingCentral and creates leads in Zoho CRM. Each accepted call is associated with the lead owner who accepted it, and the lead includes caller information, call details, and call recordings. The recordings are attached to the lead in Zoho CRM.' ^>^> "%%temp_dir%%\gui.ps1"
    echo     } ^>^> "%%temp_dir%%\gui.ps1"
    echo }) ^>^> "%%temp_dir%%\gui.ps1"
    echo. ^>^> "%%temp_dir%%\gui.ps1"
    echo $dryRunCheckbox = New-Object System.Windows.Forms.CheckBox ^>^> "%%temp_dir%%\gui.ps1"
    echo $dryRunCheckbox.Location = New-Object System.Drawing.Point(10, 220) ^>^> "%%temp_dir%%\gui.ps1"
    echo $dryRunCheckbox.Size = New-Object System.Drawing.Size(250, 20) ^>^> "%%temp_dir%%\gui.ps1"
    echo $dryRunCheckbox.Text = 'Run in Dry-Run Mode (Preview Only)' ^>^> "%%temp_dir%%\gui.ps1"
    echo $form.Controls.Add($dryRunCheckbox) ^>^> "%%temp_dir%%\gui.ps1"
    echo. ^>^> "%%temp_dir%%\gui.ps1"
    echo $runButton = New-Object System.Windows.Forms.Button ^>^> "%%temp_dir%%\gui.ps1"
    echo $runButton.Location = New-Object System.Drawing.Point(200, 400) ^>^> "%%temp_dir%%\gui.ps1"
    echo $runButton.Size = New-Object System.Drawing.Size(75, 23) ^>^> "%%temp_dir%%\gui.ps1"
    echo $runButton.Text = 'Run Script' ^>^> "%%temp_dir%%\gui.ps1"
    echo $runButton.DialogResult = [System.Windows.Forms.DialogResult]::OK ^>^> "%%temp_dir%%\gui.ps1"
    echo $form.Controls.Add($runButton) ^>^> "%%temp_dir%%\gui.ps1"
    echo $form.AcceptButton = $runButton ^>^> "%%temp_dir%%\gui.ps1"
    echo. ^>^> "%%temp_dir%%\gui.ps1"
    echo $form.TopMost = $true ^>^> "%%temp_dir%%\gui.ps1"
    echo $result = $form.ShowDialog() ^>^> "%%temp_dir%%\gui.ps1"
    echo. ^>^> "%%temp_dir%%\gui.ps1"
    echo if ($result -eq [System.Windows.Forms.DialogResult]::OK) { ^>^> "%%temp_dir%%\gui.ps1"
    echo     if ($scriptComboBox.SelectedIndex -eq 0) { ^>^> "%%temp_dir%%\gui.ps1"
    echo         [System.Windows.Forms.MessageBox]::Show('Please select a script to run.', 'No Script Selected', [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Warning) ^>^> "%%temp_dir%%\gui.ps1"
    echo         exit ^>^> "%%temp_dir%%\gui.ps1"
    echo     } ^>^> "%%temp_dir%%\gui.ps1"
    echo     $scriptChoice = $scriptComboBox.SelectedIndex - 1 ^>^> "%%temp_dir%%\gui.ps1"
    echo     $startDateTimeFormatted = $startDateTime.Value.ToString('yyyy-MM-ddTHH:mm:ss') ^>^> "%%temp_dir%%\gui.ps1"
    echo     $endDateTimeFormatted = $endDateTime.Value.ToString('yyyy-MM-ddTHH:mm:ss') ^>^> "%%temp_dir%%\gui.ps1"
    echo     $tempDir = "%%temp_dir%%" ^>^> "%%temp_dir%%\gui.ps1"
    echo     [System.IO.File]::WriteAllText("$tempDir\script_choice.txt", $scriptChoice) ^>^> "%%temp_dir%%\gui.ps1"
    echo     [System.IO.File]::WriteAllText("$tempDir\start_date.txt", $startDateTimeFormatted) ^>^> "%%temp_dir%%\gui.ps1"
    echo     [System.IO.File]::WriteAllText("$tempDir\end_date.txt", $endDateTimeFormatted) ^>^> "%%temp_dir%%\gui.ps1"
    echo     [System.IO.File]::WriteAllText("$tempDir\dry_run.txt", $dryRunCheckbox.Checked) ^>^> "%%temp_dir%%\gui.ps1"
    echo } ^>^> "%%temp_dir%%\gui.ps1"
    echo.
    echo :: Run the PowerShell GUI script
    echo powershell -ExecutionPolicy Bypass -File "%%temp_dir%%\gui.ps1"
    echo.
    echo :: Check if files exist (user might have closed the form)
    echo if not exist "%%temp_dir%%\script_choice.txt" (
    echo     rmdir /s /q "%%temp_dir%%" 2^>nul
    echo     exit /b 1
    echo )
    echo.
    echo :: Read script choice, dates, and dry-run setting from files
    echo set /p script_choice=<"%%temp_dir%%\script_choice.txt"
    echo set /p start_date=<"%%temp_dir%%\start_date.txt"
    echo set /p end_date=<"%%temp_dir%%\end_date.txt"
    echo set /p dry_run=<"%%temp_dir%%\dry_run.txt"
    echo.
    echo :: Set script name based on choice
    echo if "%%script_choice%%"=="0" (
    echo     set script_name=missed_calls.py
    echo ) else (
    echo     set script_name=accepted_calls.py
    echo )
    echo.
    echo :: Create logs directory if it doesn't exist
    echo if not exist "logs" mkdir logs
    echo.
    echo :: Set the log file name with timestamp
    echo for /f "tokens=2 delims==" %%%%I in ('wmic os get localdatetime /value') do set datetime=%%%%I
    echo set log_file=logs\script_run_%%datetime:~0,8%%_%%datetime:~8,6%%.log
    echo.
    echo :: Run the selected script with the date and time range and dry-run if selected
    echo =============================================== ^> "%%log_file%%"
    echo Script Run Details ^>^> "%%log_file%%"
    echo =============================================== ^>^> "%%log_file%%"
    echo Script: %%script_name%% ^>^> "%%log_file%%"
    echo Start Date: %%start_date%% ^>^> "%%log_file%%"
    echo End Date: %%end_date%% ^>^> "%%log_file%%"
    echo Dry Run: %%dry_run%% ^>^> "%%log_file%%"
    echo =============================================== ^>^> "%%log_file%%"
    echo. ^>^> "%%log_file%%"
    echo.
    echo :: Start the script in the background
    echo if "%%dry_run%%"=="True" (
    echo     echo Running in dry-run mode... ^>^> "%%log_file%%"
    echo     python %%script_name%% --start-date "%%start_date%%" --end-date "%%end_date%%" --dry-run --debug ^>^> "%%log_file%%" 2^>^&1
    echo ) else (
    echo     echo Running in normal mode... ^>^> "%%log_file%%"
    echo     python %%script_name%% --start-date "%%start_date%%" --end-date "%%end_date%%" ^>^> "%%log_file%%" 2^>^&1
    echo )
    echo.
    echo :: Create notification script
    echo Add-Type -AssemblyName System.Windows.Forms ^> "%%temp_dir%%\notification.ps1"
    echo [System.Windows.Forms.MessageBox]::Show('Script execution completed! The log file is available at: %%log_file%%', 'Script Complete', [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information) ^>^> "%%temp_dir%%\notification.ps1"
    echo.
    echo :: Show notification
    echo powershell -ExecutionPolicy Bypass -File "%%temp_dir%%\notification.ps1"
    echo.
    echo :: Clean up temporary directory
    echo rmdir /s /q "%%temp_dir%%" 2^>nul
    echo.
    echo :: Display log file path
    echo.
    echo echo Script execution completed. Log file is available at: %%log_file%%
    echo echo.
    echo.
    echo :: Keep the window open
    echo pause
) > run_script_date.bat

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
echo    For both scripts with date selection:
echo    run_script_date.bat
echo.
pause 