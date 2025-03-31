import os
import json
import logging
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'secure_credentials.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SecureCredentials:
    """Secure storage for API credentials"""
    def __init__(self):
        self.data_dir = Path('data')
        self.data_dir.mkdir(exist_ok=True)
        
        self.key_file = self.data_dir / 'encryption.key'
        self.credentials_file = self.data_dir / 'credentials.enc'
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

    def save_rc_credentials(self, jwt, client_id, client_secret, account_id):
        """Save RingCentral credentials"""
        try:
            credentials = self.load_credentials() or {}
            credentials.update({
                'rc_jwt': jwt,
                'rc_client_id': client_id,
                'rc_client_secret': client_secret,
                'rc_account': account_id,
                'timestamp': datetime.now().isoformat()
            })
            
            json_data = json.dumps(credentials)
            encrypted_data = self.cipher_suite.encrypt(json_data.encode())
            
            with open(self.credentials_file, 'wb') as file:
                file.write(encrypted_data)
            
            logger.info("RingCentral credentials saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving RingCentral credentials: {str(e)}")
            return False

    def save_zoho_credentials(self, client_id, client_secret, refresh_token):
        """Save Zoho credentials"""
        try:
            credentials = self.load_credentials() or {}
            credentials.update({
                'zoho_client_id': client_id,
                'zoho_client_secret': client_secret,
                'zoho_refresh_token': refresh_token,
                'timestamp': datetime.now().isoformat()
            })
            
            json_data = json.dumps(credentials)
            encrypted_data = self.cipher_suite.encrypt(json_data.encode())
            
            with open(self.credentials_file, 'wb') as file:
                file.write(encrypted_data)
            
            logger.info("Zoho credentials saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving Zoho credentials: {str(e)}")
            return False

    def load_credentials(self):
        """Load and decrypt credentials"""
        try:
            if not self.credentials_file.exists():
                return None

            with open(self.credentials_file, 'rb') as file:
                encrypted_data = file.read()
            
            decrypted_data = self.cipher_suite.decrypt(encrypted_data)
            credentials = json.loads(decrypted_data.decode())
            
            # Check if credentials are expired (1 hour)
            timestamp = datetime.fromisoformat(credentials['timestamp'])
            if datetime.now() - timestamp > timedelta(hours=1):
                logger.warning("Credentials have expired")
                return None
            
            return credentials
        except Exception as e:
            logger.error(f"Error loading credentials: {str(e)}")
            return None

    def get_rc_credentials(self):
        """Get RingCentral credentials"""
        credentials = self.load_credentials()
        if not credentials:
            return None
        
        return {
            'jwt': credentials.get('rc_jwt'),
            'client_id': credentials.get('rc_client_id'),
            'client_secret': credentials.get('rc_client_secret'),
            'account_id': credentials.get('rc_account')
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