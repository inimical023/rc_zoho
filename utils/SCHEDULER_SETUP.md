# Windows Task Scheduler Setup Guide

This guide explains how to set up automatic execution of the RingCentral-Zoho integration scripts using Windows Task Scheduler, with automatic email reporting.

## Prerequisites

1. Ensure Python is installed and in your system PATH
2. All required dependencies are installed
3. Update the email configuration at `Main/data/email_config.json` with your SMTP server details and recipient email addresses

## Setting Up Tasks in Windows Task Scheduler

### For Accepted Calls Processing

1. Open Windows Task Scheduler (search for "Task Scheduler" in the Start menu)
2. Click on "Create Task..." in the right panel
3. Fill in the following information:
   - **Name**: `RC-Zoho Accepted Calls Processing`
   - **Description**: `Processes accepted calls from RingCentral and creates leads in Zoho CRM`
   - **Run whether user is logged on or not**: Enable this option
   - **Run with highest privileges**: Enable this option
   - **Configure for**: Select your Windows version

4. Go to the "Triggers" tab and click "New..."
   - Set the task to run on a schedule (e.g., Daily at 6:00 AM)
   - You may want to set additional triggers as needed

5. Go to the "Actions" tab and click "New..."
   - **Action**: Start a program
   - **Program/script**: Browse to and select the batch file at `C:\Scripts\RC Zoho API\Main\run_accepted_calls_with_report.bat`
   - **Start in**: `C:\Scripts\RC Zoho API\Main`

6. Go to the "Conditions" tab:
   - Uncheck "Start the task only if the computer is on AC power" if this is a server
   - Make other adjustments as needed for your environment

7. Go to the "Settings" tab:
   - Set "If the task fails, restart every:" if you want automatic retry
   - Other settings can be adjusted according to your needs

8. Click "OK" to create the task

### For Missed Calls Processing

1. Repeat the steps above but with these changes:
   - **Name**: `RC-Zoho Missed Calls Processing`
   - **Program/script**: Browse to and select the batch file at `C:\Scripts\RC Zoho API\Main\run_missed_calls_with_report.bat`

## Email Configuration

The email reporting system requires valid SMTP settings. Edit the `Main/data/email_config.json` file with your actual mail server information:

```json
{
    "smtp_settings": {
        "server": "smtp.yourcompany.com",
        "port": 587,
        "username": "your_email@yourcompany.com",
        "password": "your_email_password",
        "use_tls": true,
        "from_address": "notifications@yourcompany.com"
    },
    "recipients": {
        "accepted_calls": ["recipient1@example.com", "recipient2@example.com"],
        "missed_calls": ["recipient3@example.com", "recipient4@example.com"]
    }
}
```

## Testing Your Setup

Before relying on the scheduled tasks, test each batch file manually:

1. Open Command Prompt as Administrator
2. Navigate to your script directory: `cd C:\Scripts\RC Zoho API\Main`
3. Run each batch file: `run_accepted_calls_with_report.bat` and `run_missed_calls_with_report.bat`
4. Check that the scripts execute properly and emails are sent

## Troubleshooting

If you encounter issues with the scheduled tasks:

1. **Task doesn't run**: Check the task history in Task Scheduler
2. **Script errors**: Review the log files in `Main/logs/`
3. **Email not sending**: Verify SMTP settings and check if your mail server requires additional authentication
4. **Permission issues**: Ensure the task is running with appropriate user permissions

## Security Notes

1. The email configuration file contains your SMTP password. Ensure appropriate file system permissions are set.
2. Consider using an application-specific password if your email provider supports it.
3. If possible, create a dedicated email account for these notifications rather than using a personal account.

## Advanced: Running at Different Intervals

You may want to run the accepted calls and missed calls processing at different intervals:

- **Accepted calls**: May be processed more frequently (e.g., every 2 hours)
- **Missed calls**: May be processed less frequently (e.g., once per day)

Simply create different triggers in the Task Scheduler for each task according to your business needs. 