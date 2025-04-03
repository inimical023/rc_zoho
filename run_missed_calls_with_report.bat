@echo off
REM Batch script to run missed_calls.py and then email a report
REM For use with Windows Task Scheduler

REM Change to the script directory
cd /d %~dp0

REM Run the missed_calls.py script
python missed_calls.py --hours-back 24

REM Check if the script executed successfully
if %ERRORLEVEL% NEQ 0 (
    echo Error running missed_calls.py script
    exit /b %ERRORLEVEL%
)

REM Run the email report script
python utils\email_report.py --script-type missed_calls

REM Exit with the email script's error level
exit /b %ERRORLEVEL% 