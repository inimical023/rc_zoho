from common import *   # Now you have os, sys, json, logging, etc.
import itertools  # For round-robin lead owner assignment
import argparse

# Check and install dependencies
check_and_install_dependencies()

# Initialize storage and logger
storage = SecureStorage()
logger = setup_logging("missed_calls")

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
        logging.FileHandler(os.path.join(logs_dir, 'missed_calls.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("missed_calls")


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

    def create_or_update_lead(self, call, lead_owner, extension_names):
        """Create or update a lead in Zoho CRM."""
        # Check if call has the required structure
        if not call.get('from') or not call.get('from', {}).get('phoneNumber'):
            logger.warning(f"Call is missing phone number data, skipping: {call.get('id')}")
            return
            
        phone_number = call['from']['phoneNumber']
        extension_id = call['to'].get('extensionId')
        lead_source = extension_names.get(extension_id, "Unknown")
        lead_status = "Missed Call"  # Set Lead Status to "Missed Call"
        first_name = "Unknown Caller"
        last_name = "Unknown Caller"

        existing_lead = self.search_records("Leads", f"Phone:equals:{phone_number}")

        # Extract call receive time from RingCentral API
        call_receive_time = call.get('startTime')
        if call_receive_time:
            try:
                # Convert the time to the desired format
                call_time = datetime.fromisoformat(call_receive_time.replace('Z', '+00:00')).strftime("%Y-%m-%d %H:%M:%S")
            except ValueError as e:
                logger.error(f"Error parsing startTime: {e}. Using current time.")
                call_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            call_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.warning("Call start time not found. Using current time.")

        if existing_lead:
            lead_id = existing_lead[0]['id']
            logger.info(f"Existing lead found {lead_id} for {phone_number}. Adding a note.")
            note_content = f"Missed call received on {call_time}."
            self.add_note_to_lead(lead_id, note_content)
        else:
            # Use the lead_owner['id'] directly from lead_owners.json
            lead_owner_id = lead_owner['id']
            data = {
                "data": [
                    {
                        "Phone": phone_number,
                        "Owner": {"id": lead_owner_id},
                        "Lead_Source": lead_source,
                        "Lead_Status": lead_status,
                        "First_Name": first_name,
                        "Last_Name": last_name
                    }
                ]
            }
            logger.debug(f"Creating lead data: {data}")
            if self.dry_run:
                logger.info(f"[DRY-RUN] Would have created lead with data: {data}")
            else:
                lead_id = self.create_zoho_lead(data)
                if lead_id:
                    # Add note for new lead creation
                    note_content = f"New lead created from missed call received on {call_time}."
                    self.add_note_to_lead(lead_id, note_content)
                    logger.info(f"Added creation note to new lead {lead_id}")

    def get_lead_owner_id_by_email(self, email):
        """Get the lead owner ID from Zoho CRM based on the email address."""
        if not self.access_token:
            logger.error("No access token available")
            return None

        url = f"{self.base_url}/users"
        headers = {
            "Authorization": f"Zoho-oauthtoken {self.access_token}",
            "Content-Type": "application/json"
        }
        params = {
            "criteria": f"Email:equals:{email}"
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                if data and data['data']:
                    return data['data'][0]['id']
                else:
                    logger.warning(f"No user found with email {email}")
                    return None
            else:
                logger.error(f"Error getting user with email {email}: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Exception getting user with email {email}: {e}")
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


def configure_logging(debug=False):
    """Configure logging level."""
    if debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    else:
        logger.setLevel(logging.INFO)


def load_extensions(config_path=None):
    """Load extension IDs and names from extensions.json."""
    config_file = config_path or os.path.join(data_dir, 'extensions.json')
    try:
        with open(config_file, 'r') as f:
            extensions_data = json.load(f)
        extensions = extensions_data
        extension_ids = [str(ext.get('id')) for ext in extensions if ext.get('id')]
        extension_names = {str(ext.get('id')): ext.get('name')
                           for ext in extensions if ext.get('id') and ext.get('name')}
        logger.info(
            f"Loaded {len(extension_ids)} extension IDs from {config_file}: {', '.join(extension_names.values())}")
        return extension_ids, extension_names
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_file}")
        return [], {}
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in config file: {config_file}")
        return [], {}


def load_lead_owners(config_path=None):
    """Load lead owners from lead_owners.json."""
    config_file = config_path or os.path.join(data_dir, 'lead_owners.json')
    try:
        with open(config_file, 'r') as f:
            lead_owners = json.load(f)
        logger.info(f"Loaded {len(lead_owners)} lead owners from {config_file}")
        return lead_owners
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_file}")
        return []
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in config file: {config_file}")
        return []


def get_yesterday_date_range():
    """Get yesterday's date range in ISO format."""
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    start_date = yesterday.strftime('%Y-%m-%d') + 'T00:00:00'
    end_date = yesterday.strftime('%Y-%m-%d') + 'T23:59:59'
    return start_date, end_date


def process_missed_calls(call_logs, zoho_client, extension_ids, extension_names, lead_owners, dry_run=False):
    """Process missed calls and create leads in Zoho CRM."""
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
        description='Process missed calls from RingCentral and create leads in Zoho CRM.')
    parser.add_argument(
        '--start-date', help='Start date for call logs (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date for call logs (YYYY-MM-DD)')
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
    """Main function."""
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Set up logging based on debug flag
        logger = setup_logging("missed_calls", args.debug)
        
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
            process_missed_calls(call_logs, zoho_client, extension_ids, extension_names, lead_owners, args.dry_run)
            
        logger.info("Processing completed successfully")
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise


if __name__ == "__main__":
    main()