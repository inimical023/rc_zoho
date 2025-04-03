#!/usr/bin/env python
"""
Email Report Generator
---------------------
This script generates and emails HTML reports based on the latest log files
from accepted_calls.py or missed_calls.py scripts.

Usage:
    python email_report.py --script-type [accepted_calls|missed_calls] --recipients user1@example.com,user2@example.com
    python email_report.py --script-type [accepted_calls|missed_calls] --dry-run --hours-back 24
"""

import os
import sys
import re
import argparse
import smtplib
import logging
import subprocess
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime
from pathlib import Path
import glob
import json
import socket

# Add parent directory to path so we can import common modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import common utilities
from common import setup_logging, SecureStorage, check_and_install_dependencies

# Check and install dependencies
check_and_install_dependencies()

# Setup logging
logger = setup_logging('email_report')

class EmailReporter:
    """Class to handle email reporting of script results"""
    
    def __init__(self, script_type, recipients=None, smtp_settings=None, dry_run=False, hours_back=24):
        """
        Initialize the reporter
        
        Args:
            script_type (str): Type of script - 'accepted_calls' or 'missed_calls'
            recipients (list): List of email addresses to send reports to
            smtp_settings (dict): SMTP server settings
            dry_run (bool): If True, run the script in dry-run mode before generating report
            hours_back (int): Number of hours to look back when running script in dry-run mode
        """
        self.script_type = script_type.lower()
        if self.script_type not in ['accepted_calls', 'missed_calls']:
            raise ValueError("Script type must be 'accepted_calls' or 'missed_calls'")
        
        # Get script directory path
        self.script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.logs_dir = os.path.join(self.script_dir, 'logs')
        
        # Load email configuration
        self.recipients = recipients or []
        self.load_email_config()
        
        # Override SMTP settings if provided
        if smtp_settings:
            self.smtp_settings = smtp_settings
        
        # Load credentials
        self.storage = SecureStorage()
        
        # Dry run settings
        self.dry_run = dry_run
        self.hours_back = hours_back
        
    def load_email_config(self):
        """Load email configuration from config file"""
        config_path = os.path.join(self.script_dir, 'data', 'email_config.json')
        default_config = {
            "smtp_settings": {
                "server": "smtp.example.com",
                "port": 587, 
                "username": "your_username",
                "password": "your_password",
                "use_tls": True,
                "from_address": "no-reply@example.com"
            },
            "recipients": {
                "accepted_calls": ["user1@example.com"],
                "missed_calls": ["user1@example.com"]
            }
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config = json.load(f)
                self.smtp_settings = config.get('smtp_settings', default_config['smtp_settings'])
                
                # Add recipients from config if none provided
                if not self.recipients:
                    self.recipients = config.get('recipients', {}).get(self.script_type, [])
            else:
                logger.warning(f"Email config file not found at {config_path}. Using default settings.")
                # Create default config
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                with open(config_path, 'w') as f:
                    json.dump(default_config, f, indent=4)
                self.smtp_settings = default_config['smtp_settings']
                
                if not self.recipients:
                    self.recipients = default_config['recipients'][self.script_type]
                    
        except Exception as e:
            logger.error(f"Error loading email configuration: {e}")
            self.smtp_settings = default_config['smtp_settings']
            if not self.recipients:
                self.recipients = default_config['recipients'][self.script_type]
    
    def run_script(self):
        """Run the script in dry-run mode to generate a fresh log file"""
        script_name = f"{self.script_type}.py"
        script_path = os.path.join(self.script_dir, script_name)
        
        if not os.path.exists(script_path):
            logger.error(f"Script not found: {script_path}")
            return False
            
        # Prepare command
        cmd = [
            sys.executable,
            script_path,
            "--dry-run",
            "--hours-back", str(self.hours_back),
            "--debug"
        ]
        
        logger.info(f"Running script in dry-run mode: {' '.join(cmd)}")
        
        try:
            # Run the script as a subprocess
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                cwd=self.script_dir
            )
            
            # Capture and log output
            output = []
            for line in process.stdout:
                output.append(line)
                logger.info(f"Script output: {line.strip()}")
                
            # Wait for process to complete
            process.wait()
            
            if process.returncode != 0:
                logger.error(f"Script failed with exit code {process.returncode}")
                return False
                
            logger.info(f"Script completed successfully in dry-run mode")
            return True
            
        except Exception as e:
            logger.error(f"Error running script: {e}")
            return False
    
    def find_latest_log(self):
        """Find the latest log file for the specified script type"""
        log_pattern = os.path.join(self.logs_dir, f"{self.script_type}_*.log")
        log_files = glob.glob(log_pattern)
        
        if not log_files:
            logger.error(f"No log files found matching pattern: {log_pattern}")
            return None
        
        # Sort by modification time (newest first)
        latest_log = max(log_files, key=os.path.getmtime)
        logger.info(f"Found latest log file: {latest_log}")
        return latest_log
    
    def parse_log_file(self, log_path):
        """Parse the log file to extract key statistics and events"""
        if not log_path or not os.path.exists(log_path):
            logger.error(f"Log file not found: {log_path}")
            return {}
        
        stats = {
            'script_type': self.script_type,
            'timestamp': datetime.fromtimestamp(os.path.getmtime(log_path)).strftime('%Y-%m-%d %H:%M:%S'),
            'duration': None,
            'total_calls': 0,
            'processed_calls': 0,
            'existing_leads': 0,
            'new_leads': 0,
            'failed_calls': 0,
            'skipped_calls': 0,
            'recordings_attached': 0,
            'start_time': None,
            'end_time': None,
            'date_range': None,
            'dry_run_mode': False,
            'log_entries': []
        }
        
        # Patterns to extract key information
        start_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - \w+ - INFO - (\w+)\.py - Starting at')
        end_pattern = re.compile(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) - \w+ - INFO - Processing completed successfully')
        date_range_pattern = re.compile(r'Processing (calls|MISSED calls) from (\S+) to (\S+)')
        total_calls_pattern = re.compile(r'Total calls found: (\d+)')
        processed_calls_pattern = re.compile(r'(Calls processed|Missed calls processed): (\d+)')
        existing_leads_pattern = re.compile(r'Existing leads updated: (\d+)')
        new_leads_pattern = re.compile(r'New leads created: (\d+)')
        failed_calls_pattern = re.compile(r'Failed calls: (\d+)')
        skipped_calls_pattern = re.compile(r'(Calls skipped|Other calls skipped): (\d+)')
        recordings_pattern = re.compile(r'Recordings attached: (\d+)')
        dry_run_pattern = re.compile(r'Running in dry.run mode')
        
        try:
            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                log_content = f.read()
                
                # Check if this was a dry run
                if dry_run_pattern.search(log_content):
                    stats['dry_run_mode'] = True
                
                # Extract timestamps
                start_match = start_pattern.search(log_content)
                if start_match:
                    stats['start_time'] = start_match.group(1)
                
                end_match = end_pattern.search(log_content)
                if end_match:
                    stats['end_time'] = end_match.group(1)
                
                # Calculate duration if both start and end times are available
                if stats['start_time'] and stats['end_time']:
                    start_dt = datetime.strptime(stats['start_time'], '%Y-%m-%d %H:%M:%S')
                    end_dt = datetime.strptime(stats['end_time'], '%Y-%m-%d %H:%M:%S')
                    duration = end_dt - start_dt
                    stats['duration'] = str(duration)
                
                # Extract date range
                date_range_match = date_range_pattern.search(log_content)
                if date_range_match:
                    stats['date_range'] = f"{date_range_match.group(2)} to {date_range_match.group(3)}"
                
                # Extract call statistics
                total_calls_match = total_calls_pattern.search(log_content)
                if total_calls_match:
                    stats['total_calls'] = int(total_calls_match.group(1))
                
                processed_calls_match = processed_calls_pattern.search(log_content)
                if processed_calls_match:
                    stats['processed_calls'] = int(processed_calls_match.group(2))
                
                existing_leads_match = existing_leads_pattern.search(log_content)
                if existing_leads_match:
                    stats['existing_leads'] = int(existing_leads_match.group(1))
                
                new_leads_match = new_leads_pattern.search(log_content)
                if new_leads_match:
                    new_leads_text = new_leads_match.group(1)
                    # Handle case where it shows '0 (dry run)'
                    if '(' in new_leads_text:
                        stats['new_leads'] = 0
                        stats['dry_run_mode'] = True
                    else:
                        stats['new_leads'] = int(new_leads_text)
                
                failed_calls_match = failed_calls_pattern.search(log_content)
                if failed_calls_match:
                    stats['failed_calls'] = int(failed_calls_match.group(1))
                
                skipped_calls_match = skipped_calls_pattern.search(log_content)
                if skipped_calls_match:
                    stats['skipped_calls'] = int(skipped_calls_match.group(2))
                
                recordings_match = recordings_pattern.search(log_content)
                if recordings_match:
                    stats['recordings_attached'] = int(recordings_match.group(1))
                
                # Get relevant log entries (INFO level and above)
                log_entries = []
                for line in log_content.splitlines():
                    if ' - INFO - ' in line or ' - WARNING - ' in line or ' - ERROR - ' in line:
                        log_entries.append(line)
                stats['log_entries'] = log_entries[-50:]  # Keep last 50 entries
            
            return stats
            
        except Exception as e:
            logger.error(f"Error parsing log file {log_path}: {e}")
            return stats
    
    def generate_html_report(self, stats):
        """Generate an HTML report from the parsed log statistics"""
        if not stats:
            logger.error("No statistics available to generate report")
            return None
        
        script_name = "Accepted Calls" if self.script_type == "accepted_calls" else "Missed Calls"
        report_title = f"{script_name} Processing Report - {stats.get('timestamp', 'Unknown Date')}"
        
        # Add dry run indicator to title if applicable
        if stats.get('dry_run_mode', False):
            report_title += " (DRY RUN)"
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f9f9f9;
        }}
        .container {{
            background-color: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            padding: 25px;
        }}
        header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 1px solid #eee;
        }}
        h1 {{
            color: #2c3e50;
            margin: 0;
            font-weight: 500;
        }}
        h2 {{
            color: #3498db;
            margin-top: 30px;
            margin-bottom: 15px;
            font-weight: 500;
        }}
        .timestamp {{
            color: #7f8c8d;
            font-size: 16px;
            margin-top: 10px;
        }}
        .summary-box {{
            background-color: #f8f9fa;
            border-left: 4px solid #3498db;
            padding: 15px;
            margin-bottom: 25px;
            border-radius: 4px;
        }}
        .dry-run-badge {{
            display: inline-block;
            background-color: #f39c12;
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
            font-weight: bold;
            margin-top: 10px;
        }}
        .stats-container {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background-color: #fff;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 5px rgba(0, 0, 0, 0.05);
            text-align: center;
        }}
        .stat-card h3 {{
            margin-top: 0;
            font-size: 16px;
            color: #7f8c8d;
            font-weight: normal;
        }}
        .stat-card .value {{
            font-size: 32px;
            font-weight: bold;
            color: #2c3e50;
            margin: 10px 0;
        }}
        .log-container {{
            background-color: #2c3e50;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            overflow-x: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
            margin-top: 25px;
        }}
        .log-entry {{
            margin: 5px 0;
            font-size: 14px;
            line-height: 1.5;
        }}
        .log-info {{ color: #8BC34A; }}
        .log-warning {{ color: #FFC107; }}
        .log-error {{ color: #F44336; }}
        footer {{
            text-align: center;
            margin-top: 40px;
            color: #7f8c8d;
            font-size: 14px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }}
        .success {{ color: #27ae60; }}
        .warning {{ color: #f39c12; }}
        .error {{ color: #e74c3c; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{report_title}</h1>
"""
        # Add dry run badge if applicable
        if stats.get('dry_run_mode', False):
            html += """            <div class="dry-run-badge">DRY RUN MODE - No actual changes were made</div>
"""
            
        html += f"""            <div class="timestamp">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </header>
        
        <div class="summary-box">
            <p><strong>Script:</strong> {self.script_type}.py</p>
            <p><strong>Date Range:</strong> {stats.get('date_range', 'Unknown')}</p>
            <p><strong>Execution Time:</strong> {stats.get('start_time', 'Unknown')} to {stats.get('end_time', 'Unknown')}</p>
            <p><strong>Duration:</strong> {stats.get('duration', 'Unknown')}</p>
        </div>
        
        <h2>Call Processing Statistics</h2>
        <div class="stats-container">
            <div class="stat-card">
                <h3>Total Calls</h3>
                <div class="value">{stats.get('total_calls', 0)}</div>
            </div>
            <div class="stat-card">
                <h3>Processed Calls</h3>
                <div class="value">{stats.get('processed_calls', 0)}</div>
            </div>
            <div class="stat-card">
                <h3>Existing Leads Updated</h3>
                <div class="value">{stats.get('existing_leads', 0)}</div>
            </div>
            <div class="stat-card">
                <h3>New Leads Created</h3>
                <div class="value">{stats.get('new_leads', 0)}</div>
            </div>
            <div class="stat-card">
                <h3>Skipped Calls</h3>
                <div class="value">{stats.get('skipped_calls', 0)}</div>
            </div>
            <div class="stat-card">
                <h3>Failed Calls</h3>
                <div class="value {'' if stats.get('failed_calls', 0) == 0 else 'error'}">{stats.get('failed_calls', 0)}</div>
            </div>
        """
        
        # Add recordings attached if it's accepted calls
        if self.script_type == 'accepted_calls':
            html += f"""
            <div class="stat-card">
                <h3>Recordings Attached</h3>
                <div class="value">{stats.get('recordings_attached', 0)}</div>
            </div>
            """
            
        html += """
        </div>
        
        <h2>Recent Log Entries</h2>
        <div class="log-container">
        """
        
        # Add log entries with color coding
        for entry in stats.get('log_entries', []):
            entry_class = "log-info"
            if " - WARNING - " in entry:
                entry_class = "log-warning"
            elif " - ERROR - " in entry:
                entry_class = "log-error"
                
            html += f'<div class="log-entry {entry_class}">{entry}</div>\n'
        
        html += """
        </div>
        
        <footer>
            <p>This is an automated report generated by the RingCentral-Zoho integration system.</p>
        </footer>
    </div>
</body>
</html>
"""
        
        # Create logs/reports directory if it doesn't exist
        reports_dir = os.path.join(self.logs_dir, 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        
        # Save the HTML report
        report_path = os.path.join(reports_dir, f"{self.script_type}_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html)
            
        logger.info(f"HTML report generated: {report_path}")
        return report_path
    
    def send_email_report(self, html_report_path):
        """Send the HTML report via email to specified recipients"""
        if not html_report_path or not os.path.exists(html_report_path):
            logger.error(f"HTML report not found: {html_report_path}")
            return False
            
        if not self.recipients:
            logger.error("No recipients specified for email report")
            logger.info(f"HTML report saved locally at: {html_report_path}")
            return False
            
        # Get server settings
        server = self.smtp_settings.get('server')
        port = self.smtp_settings.get('port', 587)
        username = self.smtp_settings.get('username')
        password = self.smtp_settings.get('password')
        use_tls = self.smtp_settings.get('use_tls', True)
        from_address = self.smtp_settings.get('from_address')
        
        if not all([server, username, password, from_address]):
            logger.error("SMTP settings incomplete. Check email_config.json")
            logger.info(f"HTML report saved locally at: {html_report_path}")
            return False
        
        # Create email
        msg = MIMEMultipart()
        script_name = "Accepted Calls" if self.script_type == "accepted_calls" else "Missed Calls"
        date_str = datetime.now().strftime('%Y-%m-%d')
        
        # Add dry run indicator to subject if applicable
        subject = f"{script_name} Processing Report - {date_str}"
        if self.dry_run:
            subject += " (DRY RUN)"
        
        # Set email subject and headers
        msg['Subject'] = subject
        msg['From'] = from_address
        msg['To'] = ', '.join(self.recipients)
        
        # Create an HTML version of the email body
        with open(html_report_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
        # Attach HTML version
        msg.attach(MIMEText(html_content, 'html'))
        
        # Attach the report as a file
        with open(html_report_path, 'rb') as f:
            attachment = MIMEApplication(f.read())
            attachment_name = os.path.basename(html_report_path)
            attachment.add_header('Content-Disposition', 'attachment', filename=attachment_name)
            msg.attach(attachment)
            
        try:
            # Test DNS resolution first
            try:
                logger.info(f"Testing DNS resolution for {server}")
                socket.gethostbyname(server)
                logger.info(f"DNS resolution successful for {server}")
            except socket.gaierror as e:
                logger.error(f"DNS resolution failed for {server}: {e}")
                logger.error("Please check your SMTP server address and internet connection")
                logger.info(f"HTML report saved locally at: {html_report_path}")
                return False
                
            # Connect to server and send email
            logger.info(f"Connecting to SMTP server {server}:{port}")
            
            # Set timeout for connection
            smtp = smtplib.SMTP(server, port, timeout=30)
            
            # Set debug level for more information
            smtp.set_debuglevel(1)
            
            if use_tls:
                logger.info("Starting TLS")
                smtp.starttls()
                
            logger.info(f"Logging in with username: {username}")
            smtp.login(username, password)
            
            logger.info(f"Sending email to {', '.join(self.recipients)}")
            smtp.send_message(msg)
            smtp.quit()
            
            logger.info(f"Email report sent to {', '.join(self.recipients)}")
            return True
        except socket.timeout as e:
            logger.error(f"Timeout connecting to SMTP server: {e}")
            logger.error("Check if your SMTP server is reachable and the port is correct")
            logger.info(f"HTML report saved locally at: {html_report_path}")
            return False
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            logger.error("Check your username and password")
            logger.info(f"HTML report saved locally at: {html_report_path}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            logger.info(f"HTML report saved locally at: {html_report_path}")
            return False
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            logger.info(f"HTML report saved locally at: {html_report_path}")
            return False
            
    def run(self):
        """
        Main method to generate and send email report
        """
        logger.info(f"Starting email report generation for {self.script_type}")
        
        # If dry run mode is enabled, run the script first
        if self.dry_run:
            logger.info(f"Running {self.script_type}.py in dry-run mode")
            if not self.run_script():
                logger.error("Failed to run script in dry-run mode")
                return False
        
        # Find the latest log file
        latest_log = self.find_latest_log()
        if not latest_log:
            logger.error("Cannot continue without a log file")
            return False
            
        # Parse the log file
        stats = self.parse_log_file(latest_log)
        if not stats:
            logger.error("Failed to parse log file")
            return False
            
        # Generate HTML report
        html_report = self.generate_html_report(stats)
        if not html_report:
            logger.error("Failed to generate HTML report")
            return False
        
        # If local-only mode is enabled, don't attempt to send email
        if hasattr(self, 'local_only') and self.local_only:
            logger.info(f"Local-only mode enabled. HTML report saved at: {html_report}")
            return True
            
        # Send email report
        result = self.send_email_report(html_report)
        if result:
            logger.info("Email report process completed successfully")
        else:
            logger.error("Failed to send email report")
            
        return result

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Generate and email reports based on script logs')
    parser.add_argument('--script-type', required=True, choices=['accepted_calls', 'missed_calls'],
                      help='The type of script to process logs for')
    parser.add_argument('--recipients', help='Comma-separated list of email recipients')
    parser.add_argument('--dry-run', action='store_true', help='Run the script in dry-run mode before generating report')
    parser.add_argument('--hours-back', type=int, default=24, help='Number of hours to look back when running in dry-run mode')
    parser.add_argument('--local-only', action='store_true', help='Generate HTML report locally without sending email')
    return parser.parse_args()

def main():
    """Main function"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Convert recipients string to list if provided
    recipients = args.recipients.split(',') if args.recipients else None
    
    # Create reporter and run
    try:
        reporter = EmailReporter(
            args.script_type, 
            recipients, 
            dry_run=args.dry_run,
            hours_back=args.hours_back
        )
        
        # Set local-only mode if specified
        if args.local_only:
            reporter.local_only = True
            
        result = reporter.run()
        return 0 if result else 1
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 