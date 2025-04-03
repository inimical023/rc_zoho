@echo off
REM Batch script to run accepted_calls.py and then email a report
REM For use with Windows Task Scheduler

REM Change to the script directory
cd /d %~dp0

REM Run the accepted_calls.py script
python accepted_calls.py --hours-back 24

REM Check if the script executed successfully
if %ERRORLEVEL% NEQ 0 (
    echo Error running accepted_calls.py script
    exit /b %ERRORLEVEL%
)

REM Run the email report script
python utils\email_report.py --script-type accepted_calls

REM Exit with the email script's error level
exit /b %ERRORLEVEL% 