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
- Intelligent duplicate lead prevention

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

## Changelog

### Version 1.1.0 (Current)

#### Bug Fixes
- **Fixed logger initialization issue** when running scripts from the GUI:
  - Added proper initialization of the global logger in main functions
  - Improved error handling in the Unified Admin GUI
  - Ensured scripts run from the correct working directory

#### Missed Calls Script Improvements
- **Fixed duplicate lead creation issue** with multiple layers of protection:
  - Added phone number normalization to standardize formats
  - Enhanced phone search functionality to try multiple phone formats
  - Implemented cooldown periods between processing calls from same number
  - Added final verification before creating new leads
  - Process calls in chronological order to maintain consistency

- **Improved API handling and reliability**:
  - Added robust token refresh mechanisms for both RingCentral and Zoho
  - Implemented retry logic with exponential backoff
  - Enhanced error handling and reporting
  - Added pagination support for call log retrieval
  - Better rate limiting management

- **Enhanced logging**:
  - More comprehensive debug information
  - Better tracking of processed calls
  - Detailed statistics on call processing

#### Accepted Calls Script Improvements
- **Fixed duplicate lead creation issue** with the same protections as missed calls:
  - Added phone number normalization for all incoming calls
  - Enhanced phone search with multiple format support
  - Implemented cooldown periods between processing calls from same number
  - Added final verification checks before creating new leads

- **Improved recording attachment functionality**:
  - Implemented retry logic for failed recording attachments
  - Better content type detection and handling
  - More detailed error reporting for recording failures
  - Automatic note creation when recordings cannot be attached

- **Enhanced API reliability**:
  - Improved error handling for all API interactions
  - Implemented exponential backoff for rate limited requests
  - Better token refresh mechanisms
  - Comprehensive error tracking and reporting

- **Better performance monitoring**:
  - Detailed statistics on call processing, including:
    - Duplicate prevention metrics
    - Recording attachment success/failure rates
    - API error tracking
    - Processing time metrics

### Version 1.0.0 (Initial Release)
- Initial integration between RingCentral and Zoho CRM
- Unified admin interface
- Basic call processing functionality
- Lead creation and management 