import argparse
import logging
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