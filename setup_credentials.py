import argparse
import logging
import os
import sys
import subprocess
from pathlib import Path
from secure_credentials import SecureCredentials

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/setup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('setup_credentials')

def ensure_venv_activated():
    """Ensure the virtual environment is activated"""
    if not hasattr(sys, 'real_prefix') and not hasattr(sys, 'base_prefix'):
        logger.info("Virtual environment not activated. Attempting to activate...")
        
        # Get the script's directory
        script_dir = Path(__file__).parent.absolute()
        venv_path = script_dir / 'venv' / 'Scripts' / 'activate.bat'
        
        if not venv_path.exists():
            logger.error(f"Virtual environment not found at {venv_path}")
            logger.error("Please run setup_integration.bat first to create the virtual environment.")
            sys.exit(1)
            
        try:
            # Activate the virtual environment
            activate_cmd = f'"{venv_path}" && python "{__file__}" {" ".join(sys.argv[1:])}'
            subprocess.run(activate_cmd, shell=True)
            sys.exit(0)
        except Exception as e:
            logger.error(f"Failed to activate virtual environment: {str(e)}")
            sys.exit(1)

def setup_credentials(args):
    """Set up and store credentials securely"""
    try:
        # Initialize secure credentials handler
        secure_creds = SecureCredentials()
        
        # Prepare credentials dictionary
        credentials = {
            'rc_jwt': args.rc_jwt,
            'rc_client_id': args.rc_id,
            'rc_client_secret': args.rc_secret,
            'rc_account': args.rc_account,
            'zoho_client_id': args.zoho_id,
            'zoho_client_secret': args.zoho_secret,
            'zoho_refresh_token': args.zoho_refresh
        }
        
        # Save credentials
        if secure_creds.save_credentials(credentials):
            logger.info("Credentials setup completed successfully")
            return True
        else:
            logger.error("Failed to save credentials")
            return False
            
    except Exception as e:
        logger.error(f"Error during credentials setup: {str(e)}")
        return False

def main():
    # Ensure virtual environment is activated
    ensure_venv_activated()
    
    # Import SecureCredentials after ensuring venv is activated
    from secure_credentials import SecureCredentials
    
    parser = argparse.ArgumentParser(description='Set up RingCentral and Zoho credentials')
    
    # RingCentral arguments
    parser.add_argument('--rc-jwt', required=True, help='RingCentral JWT token')
    parser.add_argument('--rc-id', required=True, help='RingCentral client ID')
    parser.add_argument('--rc-secret', required=True, help='RingCentral client secret')
    parser.add_argument('--rc-account', required=True, help='RingCentral account ID')
    
    # Zoho arguments
    parser.add_argument('--zoho-id', required=True, help='Zoho client ID')
    parser.add_argument('--zoho-secret', required=True, help='Zoho client secret')
    parser.add_argument('--zoho-refresh', required=True, help='Zoho refresh token')
    
    args = parser.parse_args()
    
    if setup_credentials(args):
        print("Credentials setup completed successfully!")
    else:
        print("Failed to set up credentials. Check the logs for details.")

if __name__ == '__main__':
    main() 