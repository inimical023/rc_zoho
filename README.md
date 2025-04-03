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
  - Added proper initialization of the global logger at the module level
  - Ensured logger is available before any code tries to use it
  - Improved error handling in the Unified Admin GUI
  - Ensured scripts run from the correct working directory
  - Fixed issue with empty log files being created on import

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

# Zoho CRM Duplicate Lead Detector

A Python utility for detecting and merging duplicate leads in Zoho CRM based on phone numbers. This script uses token-based pagination to efficiently handle large datasets (more than 2000 records) and supports flexible phone number normalization.

## Features

- **Token-based Pagination**: Can process unlimited leads from Zoho CRM, overcoming the 2000 record limit of the search endpoint
- **Phone Number Normalization**: Standardizes phone formats (removing spaces, dashes, parentheses, etc.) to detect duplicates regardless of format
- **Duplicate Detection**: Identifies leads with identical phone numbers after normalization
- **Optional Duplicate Merging**: Can merge duplicates into the oldest lead and add detailed notes about merged leads
- **Robust Error Handling**: Includes retry logic, exponential backoff, and proper error reporting
- **Detailed Logging**: Provides comprehensive logs of all operations and results
- **Customizable Limits**: Option to process only a specified number of duplicate sets for testing purposes
- **Dry Run Mode**: Test the script without making changes to Zoho CRM data

## Requirements

- Python 3.7+
- Required Python packages:
  - requests
  - cryptography (for secure credential storage)
- Zoho CRM API credentials (client ID, client secret, refresh token with appropriate permissions)

## Installation

1. Clone the repository or download the script files
2. Install required dependencies:

```bash
pip install requests cryptography
```

3. Set up your Zoho CRM API credentials (see "Credential Setup" below)

## Credential Setup

The script requires Zoho CRM API credentials stored in an encrypted file. You have two options:

### Option 1: Using the built-in credential management

1. Create a directory `data` in the same location as the script
2. Save your Zoho credentials in an encrypted file at `data/credentials.enc` with the following format:
   ```json
   {
     "zoho_client_id": "your_client_id",
     "zoho_client_secret": "your_client_secret",
     "zoho_refresh_token": "your_refresh_token"
   }
   ```
3. Save the encryption key in `data/encryption.key`

### Option 2: Using the `common` module (if available)

If you have a `common` module with a `SecureStorage` class, the script will automatically use it to load credentials.

## Usage

```bash
python detect_zoho_duplicates_token.py [--dry-run] [--merge] [--limit N]
```

### Command Line Options

- `--dry-run`: Run without making changes to Zoho CRM (recommended for initial testing)
- `--merge`: Merge duplicate leads into the oldest lead (by creation date)
- `--limit N`: Process only the first N sets of duplicates (useful for testing with a small subset)

### Examples

**Find duplicates without making changes:**
```bash
python detect_zoho_duplicates_token.py --dry-run
```

**Find duplicates and merge them (test first):**
```bash
python detect_zoho_duplicates_token.py --dry-run --merge
```

**Perform actual merge of duplicates:**
```bash
python detect_zoho_duplicates_token.py --merge
```

**Process only the first 5 duplicate sets (for testing):**
```bash
python detect_zoho_duplicates_token.py --limit 5 --dry-run --merge
```

## How It Works

The script works through the following steps:

1. **Authentication**: Connects to Zoho CRM API using OAuth 2.0 credentials
2. **Lead Retrieval**: Uses the Zoho CRM API's general records endpoint with token-based pagination to fetch all leads
3. **Phone Normalization**: For each lead, normalizes the phone number by:
   - Removing all non-digit characters (spaces, dashes, brackets, etc.)
   - Handling country codes (removes leading "1" for 11-digit US numbers)
   - Validating minimum length (10 digits)
4. **Duplicate Detection**: Groups leads by normalized phone number and identifies duplicates
5. **Report Generation**: Creates detailed CSV and JSON reports of duplicate leads
6. **Optional Merging**: If requested (with `--merge`), handles duplicate leads by:
   - Identifying the oldest lead in each duplicate set (by creation date)
   - Adding a detailed note to the oldest lead with information about the duplicates
   - Deleting the duplicate leads
   - Logging the merge operations

## Pagination Strategy

This script uses Zoho's token-based pagination instead of standard page numbers, allowing it to overcome the 2000 record limit of the search endpoint. The script:

1. Makes calls to the general records endpoint rather than the search endpoint
2. Uses the returned page token to request the next page of results
3. Continues until no more records exist or no page token is returned

## Output Files

The script generates the following output files in the `logs` directory (with timestamps):

- **CSV Report**: `zoho_duplicate_leads_token_YYYYMMDD_HHMMSS.csv`
  - Contains all duplicate leads organized by normalized phone number
  - Includes fields: Normalized Phone, Lead ID, First Name, Last Name, Original Phone, Status, Created Time, Owner

- **JSON Report**: `zoho_duplicate_leads_token_YYYYMMDD_HHMMSS.json`
  - JSON structure with normalized phone numbers as keys and arrays of duplicate lead details as values

- **Log File**: `zoho_duplicates_token_YYYYMMDD_HHMMSS.log`
  - Detailed logging of all operations, including API calls, processing steps, and any errors

## Phone Number Normalization

Phone numbers are normalized to make comparison reliable. The script:

1. Removes all non-digit characters (spaces, dashes, parentheses, dots, etc.)
2. If the number is 11 digits and starts with "1" (US country code), it removes the leading "1"
3. Validates that normalized numbers are at least 10 digits long

This means that these phone formats are considered identical:
- (202) 555-0123
- 202-555-0123
- 202.555.0123
- +1 202 555 0123
- 12025550123

## Merge Process Details

When merging duplicates (`--merge` flag), the script:

1. Sorts leads by creation date (oldest first)
2. Designates the oldest lead as the "master" lead
3. Creates a note on the master lead detailing:
   - The duplicates' IDs
   - Names
   - Phone numbers
   - Statuses
   - Owners
   - Creation dates
4. Deletes the duplicate leads from Zoho CRM
5. Generates a summary of the merge operations

## Error Handling and Resilience

The script includes several features for robust operation:

- **Exponential Backoff**: Retries API calls with increasing delays when rate limits are hit
- **Token Refresh**: Automatically refreshes the access token when it expires
- **Phone Validation**: Robust phone number parsing with clear error messages
- **Date Parsing**: Flexible ISO date parsing with fallbacks for different formats
- **Progress Tracking**: Regular progress updates for long-running operations

## Troubleshooting

### Common Issues

1. **Authentication Errors**:
   - Verify that your Zoho API credentials are correct and have the necessary permissions
   - Ensure your refresh token has not expired (typically valid for 60 days)

2. **No duplicates found**:
   - Check if leads have phone numbers in Zoho CRM
   - Verify the phone field being checked matches your Zoho CRM configuration

3. **API Rate Limiting**:
   - The script has built-in rate limit handling but may still be affected by severe limits
   - Try running with the `--limit` flag to process fewer records

4. **Empty log file**:
   - Check write permissions for the logs directory
   - Verify the script has permission to create new files

### Getting Support

If you encounter issues:

1. Check the detailed log file for error messages
2. Ensure your Zoho API credentials are valid and have the correct permissions
3. Try running with the `--dry-run` flag to test without making changes

## Performance Considerations

- The script processes records in batches of 200 (Zoho API maximum)
- For very large CRMs, the script may take significant time to complete
- Memory usage scales with the number of leads having phone numbers
- Consider using the `--limit` flag for initial testing with large datasets

## Security Notes

- API credentials are handled securely using encryption
- The script does not transmit or store lead data outside of your environment
- All sensitive output is written to local log files 

python utils/email_report.py --script-type accepted_calls --dry-run --hours-back 24 