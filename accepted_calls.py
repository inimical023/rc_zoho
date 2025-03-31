from common import *   # Now you have os, sys, json, logging, etc.
import itertools  # For round-robin lead owner assignment
import argparse
import time  # Add explicit import for time module
import subprocess
import sys
import pkg_resources

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
        'python-dotenv': '>=1.0.0,<2.0.0'
    }
    
    missing_packages = []
    
    # Check each required package
    for package, version_spec in required_packages.items():
        try:
            pkg_resources.require(f"{package}{version_spec}")
        except (pkg_resources.DistributionNotFound, pkg_resources.VersionConflict):
            missing_packages.append(f"{package}{version_spec}")
    
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

# Check and install dependencies before proceeding
check_and_install_dependencies()

# Initialize storage and logger
storage = SecureStorage()
logger = setup_logging("accepted_calls")

# Clear text credentials - REPLACE THESE WITH YOUR ACTUAL CREDENTIALS
RC_JWT_TOKEN = ""
RC_CLIENT_ID = ""
RC_CLIENT_SECRET = ""
RC_ACCOUNT_ID = "~"
ZOHO_CLIENT_ID = ""
ZOHO_CLIENT_SECRET = ""
ZOHO_REFRESH_TOKEN = ""

# Script directory and paths setup
script_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(script_dir)  # Get parent directory
data_dir = os.path.join(base_dir, 'data')
logs_dir = os.path.join(script_dir, 'logs')
os.makedirs(logs_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, 'accepted_recording.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("accepted_recording")


class RingCentralClient:
    """Client for interacting with the RingCentral API."""

    def __init__(self):
        credentials = storage.load_credentials()
        if not credentials:
            raise Exception("No RingCentral credentials found")
            
        self.jwt_token = credentials['rc_jwt']
        self.client_id = credentials['rc_client_id']
        self.client_secret = credentials['rc_client_secret']
        self.account_id = credentials['rc_account']
        self.base_url = "https://platform.ringcentral.com"
        self.access_token = None
        self._get_oauth_token()

    def _get_oauth_token(self):
        """Exchange JWT token for OAuth access token."""
        url = f"{self.base_url}/restapi/oauth/token"
        # Create Basic auth header
        auth_str = f"{self.client_id}:{self.client_secret}"
        auth_bytes = auth_str.encode('ascii')
        base64_auth = base64.b64encode(auth_bytes).decode('ascii')
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {base64_auth}"
        }
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": self.jwt_token
        }
        
        try:
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data["access_token"]
            logger.debug(f"RingCentral authentication successful. Token expires in {token_data.get('expires_in', 'unknown')} seconds")
        except Exception as e:
            logger.error(f"Error getting RingCentral token: {str(e)}")
            raise

    def get_call_logs(self, extension_id, start_date=None, end_date=None):
        """Get call logs from RingCentral API for a specific extension."""
        if not self.access_token:
            raise Exception("No OAuth access token available")

        url = f"{self.base_url}/restapi/v1.0/account/{self.account_id}/extension/{extension_id}/call-log"
        params = {
            'direction': 'Inbound',
            'type': 'Voice',
            'view': 'Detailed',
            'withRecording': 'false',
            'showBlocked': 'true',
            'showDeleted': 'false',
            'perPage': 250  # Increased perPage limit
        }

        if start_date:
            params['dateFrom'] = start_date
        if end_date:
            params['dateTo'] = end_date

        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

        logger.debug(f"API Request URL: {url}")
        logger.debug(f"API Request Parameters: {params}")
        logger.debug(f"API Request Headers: {headers}")

        response = requests.get(url, headers=headers, params=params)

        logger.debug(f"API Response Status: {response.status_code}")
        logger.debug(f"API Raw Response: {response.text[:500]}...")

        if response.status_code == 200:
            data = response.json()
            records = data.get('records', [])
            return records
        else:
            logger.error(
                f"Error getting call logs for extension {extension_id}: {response.status_code} - {response.text}")
            return []

    def get_recording_content(self, recording_id):
        """Get recording content from RingCentral API with rate limiting."""
        if not self.access_token:
            raise Exception("No OAuth access token available")

        url = f"https://media.ringcentral.com/restapi/v1.0/account/~/recording/{recording_id}/content"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
        }

        max_retries = 5  # Maximum number of retries
        backoff_factor = 2  # Exponential backoff factor
        delay = 1  # Initial delay in seconds

        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, stream=True)  # Use stream=True for large files

                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type')
                    logger.info(f"Successfully retrieved recording content for recording ID: {recording_id}")
                    return response.content, content_type  # Return content and content type

                elif response.status_code == 429:  # Too Many Requests
                    logger.warning(f"Rate limit exceeded for recording {recording_id}. Retrying in {delay} seconds...")
                    time.sleep(delay)
                    delay *= backoff_factor  # Exponential backoff
                else:
                    logger.error(
                        f"Error getting recording content for recording ID {recording_id}: {response.status_code} - {response.text}")
                    break  # Exit the loop for non-retryable errors

            except requests.exceptions.RequestException as e:
                logger.error(f"Exception getting recording content for recording ID {recording_id}: {e}")
                break

        logger.error(f"Failed to get recording content for recording ID {recording_id} after {max_retries} attempts.")
        return None, None


class ZohoClient:
    """Client for interacting with the Zoho CRM API."""

    def __init__(self, dry_run=False):
        """Initialize the Zoho client with client credentials."""
        credentials = storage.load_credentials()
        if not credentials:
            raise Exception("No Zoho credentials found")
            
        self.client_id = credentials['zoho_client_id']
        self.client_secret = credentials['zoho_client_secret']
        self.refresh_token = credentials['zoho_refresh_token']
        self.access_token = None
        self.base_url = "https://www.zohoapis.com/crm/v7"  # Default to v7
        self.dry_run = dry_run  # Add dry_run attribute
        self._get_access_token()

    def _get_access_token(self):
        """Get access token using refresh token."""
        url = "https://accounts.zoho.com/oauth/v2/token"
        data = {
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token"
        }
        
        try:
            response = requests.post(url, data=data)
            response.raise_for_status()
            token_data = response.json()
            self.access_token = token_data["access_token"]
            logger.debug(f"Zoho authentication successful. Token expires in {token_data.get('expires_in', 'unknown')} seconds")
        except Exception as e:
            logger.error(f"Error getting Zoho token: {str(e)}")
            raise

    def is_recording_already_attached(self, lead_id, recording_id):
        """Check if a recording is already attached to a lead in Zoho CRM."""
        url = f"{self.base_url}/Leads/{lead_id}/Attachments"
        headers = {
            "Authorization": f"Zoho-oauthtoken {self.access_token}",
        }
        params = {
            "fields": "id,File_Name"  # Add the required fields parameter
        }
    
        try:
            response = requests.get(url, headers=headers, params=params)
    
            if response.status_code == 200:
                attachments = response.json().get('data', [])
                for attachment in attachments:
                    if recording_id in attachment.get('File_Name', ''):
                        return True
                return False
            else:
                logger.error(f"Error checking attachments for lead {lead_id}. Status code: {response.status_code}, Response: {response.text}")
                return False
    
        except Exception as e:
            logger.error(f"Exception checking attachments for lead {lead_id}: {e}")
            return False
        
    def attach_recording_to_lead(self, call, lead_id, rc_client, call_time):
        """Attach a recording to a lead in Zoho CRM, or add a note if no recording exists."""
        if 'recording' in call and call['recording'] and 'id' in call['recording']:
            recording_id = call['recording']['id']
            logger.info(f"Checking if recording {recording_id} is already attached to lead {lead_id}")
    
            # Check if the recording is already attached
            if self.is_recording_already_attached(lead_id, recording_id):
                logger.info(f"Recording {recording_id} is already attached to lead {lead_id}. Skipping.")
                return
    
            logger.info(f"Attempting to attach recording {recording_id} to lead {lead_id}")
    
            recording_content, content_type = rc_client.get_recording_content(recording_id)
    
            if recording_content:
                # Format the call time for the filename
                formatted_call_time = call_time.strftime("%Y%m%d_%H%M%S")
    
                # Zoho API endpoint for attaching files
                url = f"{self.base_url}/Leads/{lead_id}/Attachments"
                headers = {
                    "Authorization": f"Zoho-oauthtoken {self.access_token}",
                }
                # Create the filename with the formatted call time
                filename = f"{formatted_call_time}_recording_{recording_id}.{content_type.split('/')[1]}"
                files = {
                    # Set filename and content type
                    'file': (filename, recording_content, content_type)
                }
    
                try:
                    response = requests.post(url, headers=headers, files=files)
    
                    if response.status_code in [200, 201, 202]:
                        logger.info(f"Successfully attached recording {recording_id} to lead {lead_id}")
                    else:
                        logger.error(
                            f"Error attaching recording {recording_id} to lead {lead_id}. Status code: {response.status_code}, Response: {response.text}")
                        # Add a note about the failed recording attachment
                        self.add_note_to_lead(lead_id, f"Failed to attach recording {recording_id} at {call_time.strftime('%Y-%m-%d %H:%M:%S')}. Error: {response.status_code}")
    
                except Exception as e:
                    logger.error(f"Exception attaching recording {recording_id} to lead {lead_id}: {e}")
                    # Add a note about the failed recording attachment
                    self.add_note_to_lead(lead_id, f"Failed to attach recording {recording_id} at {call_time.strftime('%Y-%m-%d %H:%M:%S')}. Error: {str(e)}")
            else:
                logger.warning(f"Could not retrieve recording content for recording ID: {recording_id}")
                # Add a note about the unavailable recording content
                self.add_note_to_lead(lead_id, f"Recording {recording_id} at {call_time.strftime('%Y-%m-%d %H:%M:%S')} could not be retrieved.")
        else:
            logger.info("No recording ID found for this call.")
            # Add a note that no recording was available for this call
            self.add_note_to_lead(lead_id, f"No recording was available for call at {call_time.strftime('%Y-%m-%d %H:%M:%S')}.")

    def create_zoho_lead(self, lead_data):
        """Create a new lead in Zoho CRM."""
        if not self.access_token:
            logger.error("No access token available")
            return None

        url = f"{self.base_url}/Leads"
        headers = {
            "Authorization": f"Zoho-oauthtoken {self.access_token}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(url, headers=headers, json=lead_data)
            if response.status_code == 201:
                data = response.json()
                if data and data['data']:
                    lead_id = data['data'][0]['id']
                    logger.info(f"Successfully created lead {lead_id}")
                    return lead_id
                else:
                    logger.error("No lead ID in response data")
                    return None
            else:
                logger.error(f"Error creating lead: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Exception creating lead: {e}")
            return None

    def search_records(self, module, criteria):
        """Search for records in Zoho CRM."""
        if not self.access_token:
            logger.error("No access token available")
            return None

        url = f"{self.base_url}/{module}/search"
        headers = {
            "Authorization": f"Zoho-oauthtoken {self.access_token}",
            "Content-Type": "application/json"
        }
        params = {
            "criteria": criteria
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                if data and data['data']:
                    return data['data']
                else:
                    logger.warning(f"No records found matching criteria: {criteria}")
                    return None
            else:
                logger.error(f"Error searching records: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Exception searching records: {e}")
            return None

    def add_note_to_lead(self, lead_id, note_content):
        """Add a note to a lead in Zoho CRM."""
        access_token = self.access_token
        if not access_token:
            logger.error("No access token provided for adding note")
            return None

        logger.info(f"Adding note to lead {lead_id}")

        # Set up the request
        url = f"https://www.zohoapis.com/crm/v7/Leads/{lead_id}/Notes"
        headers = {
            "Authorization": f"Zoho-oauthtoken {access_token}",
            "Content-Type": "application/json"
        }
        data = {
            "data": [
                {
                    "Note_Title": "Call Information",
                    "Note_Content": note_content
                }
            ]
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 201:
                logger.info(f"Successfully added note to lead {lead_id}")
                return response.json()
            else:
                logger.error(f"Error adding note to lead {lead_id}: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Exception adding note to lead {lead_id}: {e}")
            return None

def process_accepted_calls(call_logs, zoho_client, extension_ids, extension_names, lead_owners, dry_run=False):
    """Process accepted calls and create leads in Zoho CRM."""
    if not call_logs:
        logger.warning("No call logs to process")
        return

    # Create a round-robin iterator for lead owners
    lead_owner_cycle = itertools.cycle(lead_owners)
    
    for call in call_logs:
        # Skip calls that don't have the required data
        if not call.get('from') or not call.get('to'):
            logger.warning(f"Skipping call {call.get('id')} - missing required data")
            continue
            
        # Get the extension ID from the call
        extension_id = call['to'].get('extensionId')
        if not extension_id or extension_id not in extension_ids:
            logger.warning(f"Skipping call {call.get('id')} - extension {extension_id} not in configured extensions")
            continue
            
        # Get the next lead owner in the round-robin cycle
        lead_owner = next(lead_owner_cycle)
        
        # Create or update the lead in Zoho CRM
        zoho_client.create_or_update_lead(call, lead_owner, extension_names)

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Process accepted calls with recordings from RingCentral and create leads in Zoho CRM.')
    parser.add_argument(
        '--start-date', help='Start date for call logs (YYYY-MM-DDThh:mm:ss)')
    parser.add_argument('--end-date', help='End date for call logs (YYYY-MM-DDThh:mm:ss)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    parser.add_argument('--dry-run', action='store_true',
                        help='Run the script without making any changes to Zoho CRM')
    parser.add_argument('--extensions-file', help='Path to extensions.json file')
    parser.add_argument('--lead-owners-file', help='Path to lead_owners.json file')
    parser.add_argument('--log-file', help='Path to log file')
    
    # Add command-line arguments for credentials
    parser.add_argument('--rc-jwt', help='RingCentral JWT token')
    parser.add_argument('--rc-id', help='RingCentral client ID')
    parser.add_argument('--rc-secret', help='RingCentral client secret')
    parser.add_argument('--rc-account', help='RingCentral account ID')
    parser.add_argument('--zoho-id', help='Zoho client ID')
    parser.add_argument('--zoho-secret', help='Zoho client secret')
    parser.add_argument('--zoho-refresh', help='Zoho refresh token')
    
    return parser.parse_args()

def main():
    """Main function"""
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Set up logging based on debug flag
        logger = setup_logging("accepted_calls", args.debug)
        
        # Get date range for processing
        start_date, end_date = get_date_range(args.hours_back, args.start_date, args.end_date)
        logger.info(f"Processing calls from {start_date} to {end_date}")
        
        # Initialize clients
        rc_client = RingCentralClient()
        zoho_client = ZohoClient(dry_run=args.dry_run)
        
        # Load extensions and lead owners
        extensions = storage.load_extensions()
        lead_owners = storage.load_lead_owners()
        
        if not extensions:
            logger.error("No extensions configured")
            return
            
        if not lead_owners:
            logger.error("No lead owners configured")
            return
            
        # Create extension mapping
        extension_ids = {ext['id'] for ext in extensions}
        extension_names = {ext['id']: ext['name'] for ext in extensions}
        
        # Process each extension
        for extension in extensions:
            logger.info(f"Processing calls for extension {extension['name']}")
            call_logs = rc_client.get_call_logs(extension['id'], start_date, end_date)
            process_accepted_calls(call_logs, zoho_client, extension_ids, extension_names, lead_owners, args.dry_run)
            
        logger.info("Processing completed successfully")
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise

if __name__ == "__main__":
    main()