import os
import sys
import json
import logging
import requests
import base64
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import subprocess

# Try to import pkg_resources, but provide a fallback if it's not available
try:
    import pkg_resources
    HAS_PKG_RESOURCES = True
except ImportError:
    HAS_PKG_RESOURCES = False
    print("Warning: pkg_resources not found. Dependency checking will be limited.")

# Standard logging format and configuration
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

def check_and_install_dependencies():
    """Check and install required dependencies."""
    required_packages = {
        'requests': '>=2.31.0,<3.0.0',
        'cryptography': '>=41.0.0,<42.0.0',
        'python-dateutil': '>=2.8.2,<3.0.0',
        'pytz': '>=2023.3,<2024.0',
        'urllib3': '>=2.0.7,<3.0.0',
        'certifi': '>=2023.7.22,<2024.0',
        'charset-normalizer': '>=3.3.0,<4.0.0',
        'idna': '>=3.4,<4.0.0',
        'python-dotenv': '>=1.0.0,<2.0.0',
        'setuptools': '>=40.0.0'
    }
    
    missing_packages = []
    
    # Check each required package
    if HAS_PKG_RESOURCES:
        # Use pkg_resources if available
        for package, version_spec in required_packages.items():
            try:
                pkg_resources.require(f"{package}{version_spec}")
            except (pkg_resources.DistributionNotFound, pkg_resources.VersionConflict):
                missing_packages.append(f"{package}{version_spec}")
    else:
        # Fallback method if pkg_resources is not available
        # Just check if packages can be imported
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(f"{package}")
    
    if missing_packages:
        print("Installing required dependencies...")
        try:
            # Use pip to install missing packages
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
            print("Successfully installed all required dependencies.")
        except subprocess.CalledProcessError as e:
            print(f"Error installing dependencies: {e}")
            print("Please try installing the requirements manually using:")
            print(f"pip install {' '.join(missing_packages)}")
            sys.exit(1)

class SecureStorage:
    """Secure storage for credentials and configuration"""
    def __init__(self):
        load_dotenv()
        # Get the script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Use data directory inside the script directory
        self.data_dir = Path(script_dir) / 'data'
        self.data_dir.mkdir(exist_ok=True)
        
        # Create logs directory if it doesn't exist
        logs_dir = Path(script_dir) / 'logs'
        logs_dir.mkdir(exist_ok=True)
        
        self.key_file = self.data_dir / 'encryption.key'
        self.credentials_file = self.data_dir / 'credentials.enc'
        self.extensions_file = self.data_dir / 'extensions.json'
        self.lead_owners_file = self.data_dir / 'lead_owners.json'
        self._initialize_encryption()

    def _initialize_encryption(self):
        """Initialize or load encryption key"""
        try:
            if not self.key_file.exists():
                key = Fernet.generate_key()
                with open(self.key_file, 'wb') as key_file:
                    key_file.write(key)
                self.key = key
            else:
                with open(self.key_file, 'rb') as key_file:
                    self.key = key_file.read()
            self.cipher_suite = Fernet(self.key)
        except Exception as e:
            logger.error(f"Error initializing encryption: {str(e)}")
            raise

    def load_credentials(self):
        """Load and decrypt credentials"""
        try:
            if not self.credentials_file.exists():
                return None

            with open(self.credentials_file, 'rb') as file:
                encrypted_data = file.read()
            
            decrypted_data = self.cipher_suite.decrypt(encrypted_data)
            credentials = json.loads(decrypted_data.decode())
            
            return credentials
        except Exception as e:
            logger.error(f"Error loading credentials: {str(e)}")
            return None

    def load_extensions(self):
        """Load extensions configuration"""
        try:
            if not self.extensions_file.exists():
                return []
            with open(self.extensions_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading extensions: {str(e)}")
            return []

    def load_lead_owners(self):
        """Load lead owners configuration"""
        try:
            if not self.lead_owners_file.exists():
                return []
            with open(self.lead_owners_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading lead owners: {str(e)}")
            return []

def setup_logging(logger_name):
    """Configure logging with consistent format and handlers"""
    logger = logging.getLogger(logger_name)
    
    # Check if logger already has handlers to avoid duplicate output
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.INFO)
    
    # Get the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = Path(script_dir) / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    # Create handlers
    file_handler = logging.FileHandler(logs_dir / f'{logger_name}.log')
    console_handler = logging.StreamHandler()
    
    # Create formatters and add it to handlers
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Process RingCentral calls and create Zoho leads')
    parser.add_argument('--start-date', help='Start date in YYYY-MM-DD HH:MM:SS format')
    parser.add_argument('--end-date', help='End date in YYYY-MM-DD HH:MM:SS format')
    parser.add_argument('--hours-back', type=int, help='Hours of data to process')
    parser.add_argument('--dry-run', action='store_true', help='Run in dry-run mode')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    return parser.parse_args()

def get_date_range(hours_back=None, start_date=None, end_date=None):
    """Get date range for processing"""
    if start_date and end_date:
        return start_date, end_date
    
    if hours_back:
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=hours_back)
        return start_date.strftime("%Y-%m-%d %H:%M:%S"), end_date.strftime("%Y-%m-%d %H:%M:%S")
    
    # Default to last 24 hours
    end_date = datetime.now()
    start_date = end_date - timedelta(hours=24)
    return start_date.strftime("%Y-%m-%d %H:%M:%S"), end_date.strftime("%Y-%m-%d %H:%M:%S") 