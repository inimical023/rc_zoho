# RingCentral-Zoho Integration

A unified admin interface for managing RingCentral and Zoho CRM integration.

## Quick Installation

Run this command in PowerShell:
```powershell
iwr -useb https://raw.githubusercontent.com/inimical023/rc_zoho/main/install.ps1 | iex
```

## Features

- Unified GUI for managing RingCentral and Zoho CRM integration
- Secure credential management
- Call queue extension management
- Lead owner management
- Automated lead creation from calls
- Call recording attachment to leads

## Requirements

- Windows 10 or later
- Python 3.8 or later
- Internet connection for installation

## Manual Installation

1. Clone the repository
2. Run `setup_integration.bat`
3. Configure credentials using the GUI
4. Launch the admin interface using `launch_admin.bat`

## Directory Structure

```
RingCentralZoho/
├── data/               # Configuration and data storage
├── logs/              # Log files
├── .venv/             # Python virtual environment
├── unified_admin.py   # Main GUI application
├── launch_admin.bat   # GUI launcher
└── ... other scripts
```

## Configuration

1. RingCentral credentials required:
   - JWT Token
   - Client ID
   - Client Secret
   - Account ID

2. Zoho CRM credentials required:
   - Client ID
   - Client Secret
   - Refresh Token

## Usage

1. Double-click `launch_admin.bat` or use the desktop shortcut
2. Use the "Setup Credentials" tab to configure API access
3. Manage extensions and lead owners using respective tabs
4. Run call processing scripts with date ranges

## Troubleshooting

Check the `logs` directory for detailed error messages and application logs. 