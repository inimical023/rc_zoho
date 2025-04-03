# Email Reporting System

This directory contains utilities for sending automated email reports after running the RingCentral-Zoho integration scripts.

## Main Components

- `email_report.py`: Script that finds the latest log file from accepted_calls.py or missed_calls.py, generates an HTML report, and emails it to specified recipients.

## How It Works

1. The script analyzes log files to extract statistics about call processing results
2. It generates a detailed HTML report with:
   - Summary of execution details (dates, times, duration)
   - Visual statistics showing processed calls, leads created, etc.
   - Recent log entries for troubleshooting
3. The report is emailed to configured recipients
4. A copy of the HTML report is saved in the `logs/reports/` directory

## Usage

There are two ways to use this system:

### 1. Using the Batch Files (Recommended for Scheduled Tasks)

Use the provided batch files in the main directory:
- `run_accepted_calls_with_report.bat` - Runs accepted_calls.py and then emails a report
- `run_missed_calls_with_report.bat` - Runs missed_calls.py and then emails a report

These are configured to run with Windows Task Scheduler. See `SCHEDULER_SETUP.md` for details.

### 2. Running the Email Report Script Directly

If you want to generate and send a report about a script that's already been run:

```
python utils/email_report.py --script-type accepted_calls
python utils/email_report.py --script-type missed_calls
```

Optional parameters:
- `--recipients email1@example.com,email2@example.com` - Override the default recipients

## Configuration

Email settings are stored in `Main/data/email_config.json`. You must edit this file with your actual SMTP server details:

```json
{
    "smtp_settings": {
        "server": "your-smtp-server.com",
        "port": 587,
        "username": "your-username",
        "password": "your-password",
        "use_tls": true,
        "from_address": "from-address@example.com"
    },
    "recipients": {
        "accepted_calls": ["recipient1@example.com"],
        "missed_calls": ["recipient2@example.com"]
    }
}
```

## Troubleshooting

- **No email sent**: Check the logs in `logs/email_report.log`
- **SMTP errors**: Verify your email configuration settings
- **No log files found**: Make sure the script_type matches the executed script name
- **HTML report missing information**: Check if your log files contain all the expected information 