import os
import json
import logging
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/credentials.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('secure_credentials')

class SecureCredentials:
    def __init__(self):
        load_dotenv()
        self.key_file = 'data/encryption.key'
        self.credentials_file = 'data/credentials.enc'
        self._initialize_encryption()

    def _initialize_encryption(self):
        """Initialize or load encryption key"""
        if not os.path.exists(self.key_file):
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as key_file:
                key_file.write(key)
            self.key = key
        else:
            with open(self.key_file, 'rb') as key_file:
                self.key = key_file.read()
        self.cipher_suite = Fernet(self.key)

    def save_credentials(self, credentials):
        """Save encrypted credentials"""
        try:
            # Add timestamp to credentials
            credentials['timestamp'] = datetime.now().isoformat()
            
            # Convert to JSON and encrypt
            json_data = json.dumps(credentials)
            encrypted_data = self.cipher_suite.encrypt(json_data.encode())
            
            # Save to file
            with open(self.credentials_file, 'wb') as file:
                file.write(encrypted_data)
            
            logger.info("Credentials saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving credentials: {str(e)}")
            return False

    def load_credentials(self):
        """Load and decrypt credentials"""
        try:
            if not os.path.exists(self.credentials_file):
                logger.warning("No credentials file found")
                return None

            # Read and decrypt data
            with open(self.credentials_file, 'rb') as file:
                encrypted_data = file.read()
            
            decrypted_data = self.cipher_suite.decrypt(encrypted_data)
            credentials = json.loads(decrypted_data.decode())
            
            # Check if credentials are expired (older than 1 hour)
            timestamp = datetime.fromisoformat(credentials['timestamp'])
            if datetime.now() - timestamp > timedelta(hours=1):
                logger.warning("Credentials are expired")
                return None
            
            logger.info("Credentials loaded successfully")
            return credentials
        except Exception as e:
            logger.error(f"Error loading credentials: {str(e)}")
            return None

    def get_ringcentral_credentials(self):
        """Get RingCentral credentials"""
        credentials = self.load_credentials()
        if not credentials:
            return None
        return {
            'jwt': credentials.get('rc_jwt'),
            'client_id': credentials.get('rc_client_id'),
            'client_secret': credentials.get('rc_client_secret'),
            'account': credentials.get('rc_account')
        }

    def get_zoho_credentials(self):
        """Get Zoho credentials"""
        credentials = self.load_credentials()
        if not credentials:
            return None
        return {
            'client_id': credentials.get('zoho_client_id'),
            'client_secret': credentials.get('zoho_client_secret'),
            'refresh_token': credentials.get('zoho_refresh_token')
        } 