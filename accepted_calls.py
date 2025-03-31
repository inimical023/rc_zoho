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
        'pycredlib': '>=1.0.0,<2.0.0',
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

    def __init__(self, jwt_token, client_id, client_secret, account_id):
        self.jwt_token = jwt_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.account_id = account_id
        self.base_url = "https://platform.ringcentral.com"
        self.access_token = None
        self._get_oauth_token()

    def _get_oauth_token(self):
        """Exchange JWT token for OAuth access token."""
        auth_string = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()).decode()
        headers = {
            'Authorization': f'Basic {auth_string}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion': self.jwt_token
        }
        response = requests.post(
            f"{self.base_url}/restapi/oauth/token",
            headers=headers,
            data=data
        )
        if response.status_code == 200:
            self.access_token = response.json()['access_token']
            logger.debug("Successfully obtained OAuth access token")
        else:
            logger.error(
                f"Failed to obtain OAuth token: {response.status_code} - {response.text}")
            raise Exception(
                f"Failed to obtain OAuth token: {response.status_code} - {response.text}")

    def get_call_logs(self, extension_id, start_date=None, end_date=None):
        """Get call logs from RingCentral API for a specific extension."""
        if not self.access_token:
            raise Exception("No OAuth access token available")

        url = f"{self.base_url}/restapi/v1.0/account/{self.account_id}/extension/{extension_id}/call-log"
        params = {
            'direction': 'Inbound',
            'type': 'Voice',
            'view': 'Detailed',
            'withRecording': 'true',
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

        response = requests.get(url, headers=headers, params=params)

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

    def __init__(self, client_id, client_secret, refresh_token, dry_run=False):
        """Initialize the Zoho client with client credentials."""
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.access_token = None
        self.base_url = "https://www.zohoapis.com/crm/v7"  # Default to v7
        self.dry_run = dry_run  # Add dry_run attribute
        self._get_access_token()

    def _get_access_token(self):
        """Get access token using refresh token."""
        url = "https://accounts.zoho.com/oauth/v2/token"
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': self.refresh_token,
            'grant_type': 'refresh_token'
        }
        response = requests.post(url, data=data)
        if response.status_code == 200:
            self.access_token = response.json()['access_token']
            logger.debug("Successfully obtained Zoho access token")
        else:
            logger.error(
                f"Failed to obtain Zoho access token: {response.status_code} - {response.text}")
            raise Exception(
                f"Failed to obtain Zoho access token: {response.status_code} - {response.text}")

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
        """Create a lead in Zoho CRM using v7 API."""
        access_token = self.access_token
        if not access_token:
            logger.error("No access token provided for creating lead")
            return None

        logger.info(f"Creating Zoho lead with v7 API")

        # Set up the request
        url_v7 = f"https://www.zohoapis.com/crm/v7/Leads"
        headers = {
            "Authorization": f"Zoho-oauthtoken {access_token}",
            "Content-Type": "application/json"
        }

        try:
            # Make the API call
            response = requests.post(url_v7, headers=headers, json=lead_data)

            # Check if successful
            if response.status_code == 201:
                data = response.json()
                lead_id = data.get("data", [{}]
                                   )[0].get("details", {}).get("id")
                logger.info(
                    f"Successfully created Zoho lead with v7 API, ID: {lead_id}")
                return lead_id
            else:
                logger.error(
                    f"Error creating Zoho lead with v7 API. Status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None

        except Exception as e:
            logger.error(f"Exception creating Zoho lead with v7 API: {e}")
            return None
        
    def create_or_update_lead(self, call, lead_owner, extension_names, rc_client):
        """Create or update a lead in Zoho CRM based on the call details."""
        phone_number = call.get('from', {}).get('phoneNumber')
        if not phone_number:
            logger.warning(f"Call {call.get('id')} does not have a valid phone number. Skipping.")
            return
    
        # Set static values for first and last name
        first_name = "Unknown"
        last_name = "Caller"
        
        # Get extension info for lead source
        extension_id = call['to'].get('extensionId')
        lead_source = extension_names.get(str(extension_id), "Unknown")
        
        # Set lead status for accepted calls
        lead_status = "Accepted Call"
        
        # Search for an existing lead by phone number
        criteria = f"(Phone:equals:{phone_number})"
        existing_leads = self.search_records("Leads", criteria)
    
        if existing_leads:
            # Update the existing lead
            lead_id = existing_leads[0].get('id')
            logger.info(f"Found existing lead for phone number {phone_number}. Updating lead ID: {lead_id}")
            
            update_data = {
                "data": [
                    {
                        "id": lead_id,
                        "Last_Call_Time": call.get('startTime'),
                        "Lead_Status": lead_status
                    }
                ]
            }
            
            self.update_record("Leads", update_data)
            
            # Attach the recording to the existing lead
            call_time = datetime.strptime(call.get('startTime'), "%Y-%m-%dT%H:%M:%S.%fZ")
            self.attach_recording_to_lead(call, lead_id, rc_client, call_time)
        else:
            # Create a new lead
            logger.info(f"No existing lead found for phone number {phone_number}. Creating a new lead.")
            
            # Prepare lead data with correct field names and format
            lead_data = {
                "data": [
                    {
                        "First_Name": first_name,
                        "Last_Name": last_name,
                        "Phone": phone_number,
                        "Lead_Source": lead_source,
                        "Lead_Status": lead_status,
                        "Last_Call_Time": call.get('startTime')
                    }
                ]
            }
            
            # Add owner if available, in the correct format
            if lead_owner and lead_owner.get('id'):
                lead_data['data'][0]['Owner'] = {"id": lead_owner.get('id')}
                
            lead_id = self.create_zoho_lead(lead_data)
            if lead_id:
                # Attach the recording to the new lead
                call_time = datetime.strptime(call.get('startTime'), "%Y-%m-%dT%H:%M:%S.%fZ")
                self.attach_recording_to_lead(call, lead_id, rc_client, call_time) 

    def search_records(self, module, criteria):
        """Search for records in Zoho CRM."""
        if not self.access_token:
            logger.error("No access token available")
            raise Exception("No access token available")

        url = f"{self.base_url}/{module}/search"
        headers = {
            "Authorization": f"Zoho-oauthtoken {self.access_token}",
            "Content-Type": "application/json"
        }
        params = {
            "criteria": criteria
        }
        logger.debug(
            f"Search URL: {url}, Headers: {headers}, Params: {params}")  # Log search details
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            return data.get("data", [])
        else:
            logger.error(
                f"Error searching records: {response.status_code} - {response.text}")
            return []

    def update_record(self, module, data):
        """Update a record in Zoho CRM."""
        if not self.access_token:
            logger.error("No access token available")
            raise Exception("No access token available")

        url = f"{self.base_url}/{module}"
        headers = {
            "Authorization": f"Zoho-oauthtoken {self.access_token}",
            "Content-Type": "application/json"
        }
        logger.debug(
            f"Update URL: {url}, Headers: {headers}, Data: {data}")  # Log update details
        response = requests.put(url, headers=headers, json=data)

        if response.status_code in [200, 202]:
            logger.info(
                f"Successfully updated record. Status code: {response.status_code}")
            return response.json()
        else:
            logger.error(
                f"Error updating record: {response.status_code} - {response.text}")
            raise Exception(
                f"Error updating record: {response.status_code} - {response.text}")

def configure_logging(debug=False):
    """Configure logging level."""
    if debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    else:
        logger.setLevel(logging.INFO)

def add_note_to_lead(self, lead_id, note_content):
    """Add a note to a lead in Zoho CRM."""
    if not self.access_token:
        logger.error("No access token available")
        raise Exception("No access token available")

    if self.dry_run:
        logger.info(f"DRY RUN: Would add note to lead {lead_id}: {note_content}")
        return True

    url = f"{self.base_url}/Leads/{lead_id}/Notes"
    headers = {
        "Authorization": f"Zoho-oauthtoken {self.access_token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "data": [
            {
                "Note_Title": "Call Recording Information",
                "Note_Content": note_content
            }
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code in [200, 201, 202]:
            logger.info(f"Successfully added note to lead {lead_id}")
            return True
        else:
            logger.error(f"Error adding note to lead {lead_id}. Status code: {response.status_code}, Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Exception adding note to lead {lead_id}: {e}")
        return False

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


def qualify_call(call, extension_names, lead_owners):
    """Qualify a call based on certain criteria."""
    # Check if the call has any legs
    if 'legs' not in call or not call['legs']:
        return False, {'reason': 'No call legs found'}

    # Iterate through the legs to find an 'Accepted' result and a lead owner name
    for leg in call['legs']:
        leg_result = leg.get('result')
        if leg_result == 'Accepted':
            # Get the 'to' name from the leg
            leg_to_name = leg['to'].get('name')
            leg_to_extension_id = leg['to'].get('extensionId')

            # Check if the 'to' name matches a lead owner's name
            if leg_to_name:
                # Find the lead owner by name
                lead_owner = next(
                    (owner for owner in lead_owners if owner['name'] == leg_to_name), None)
                if lead_owner:
                    return True, {'details': {'lead_owner': lead_owner}}
                else:
                    logger.info(
                        f"Call ID {call.get('id')}, Leg to.name: {leg_to_name}")
            elif leg_to_extension_id:
                extension_name = extension_names.get(leg_to_extension_id)
                return True, {'details': {'extension_name': extension_name}}
            else:
                return False, {'reason': 'No lead owner found for accepted call'}

    return False, {'reason': 'No leg with \'Accepted\' result and a lead owner name'}


def process_accepted_calls(call_logs, zoho_client, extension_ids, extension_names, lead_owners, rc_client, dry_run=False):
    """Process accepted calls and update Zoho CRM."""
    qualified_calls = []
    processed_count = 0
    skipped_count = 0

    for call in call_logs:
        # Skip invalid calls
        if not call.get('from') or not call.get('from', {}).get('phoneNumber'):
            logger.warning(f"Call has invalid structure, skipping: {call.get('id')}")
            skipped_count += 1
            continue
            
        is_qualified, decision_data = qualify_call(
            call, extension_names, lead_owners)
        if is_qualified:
            # Extract lead owner information
            if 'lead_owner' in decision_data['details']:
                lead_owner_name = decision_data['details']['lead_owner']['name']
                lead_owner_id = decision_data['details']['lead_owner']['id']
            elif 'extension_name' in decision_data['details']:
                lead_owner_name = decision_data['details']['extension_name']
                lead_owner_id = None  # No lead owner ID in this case
            else:
                logger.warning(
                    f"No lead owner information found for call {call.get('id')}")
                skipped_count += 1
                continue  # Skip this call

            lead_owner = next(
                (owner for owner in lead_owners if owner['id'] == lead_owner_id), None)
            if lead_owner or lead_owner_id is None:  # Allow None lead_owner_id
                zoho_client.create_or_update_lead(
                    call, lead_owner, extension_names, rc_client)
                logger.info(
                    f"Processed call {call.get('id')} - Lead Owner: {lead_owner_name}")
                processed_count += 1
            else:
                logger.warning(
                    f"No lead owner found for call {call.get('id')}")
                skipped_count += 1
        else:
            logger.info(
                f"Skipped call {call.get('id')} - Reason: {decision_data['reason']}")
            skipped_count += 1
            
        # Add a small delay between processing calls to respect rate limits
        time.sleep(0.5)  # Reduced from 1 second to 0.5 seconds since we now have proper rate limiting
    
    logger.info(f"Summary: Processed {processed_count} accepted calls, skipped {skipped_count} calls")

    return qualified_calls


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
    """Main function."""
    args = parse_arguments()
    
    # Configure logging
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")
    
    # Use custom log file if specified
    if args.log_file:
        for handler in logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                logger.removeHandler(handler)
        logger.addHandler(logging.FileHandler(args.log_file))
        logger.info(f"Logging to custom log file: {args.log_file}")

    # Use command-line arguments for credentials
    global RC_JWT_TOKEN, RC_CLIENT_ID, RC_CLIENT_SECRET, RC_ACCOUNT_ID
    global ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REFRESH_TOKEN
    
    # RingCentral credentials from command line
    if args.rc_jwt:
        RC_JWT_TOKEN = args.rc_jwt
    if args.rc_id:
        RC_CLIENT_ID = args.rc_id
    if args.rc_secret:
        RC_CLIENT_SECRET = args.rc_secret
    if args.rc_account:
        RC_ACCOUNT_ID = args.rc_account
        
    # Zoho credentials from command line
    if args.zoho_id:
        ZOHO_CLIENT_ID = args.zoho_id
    if args.zoho_secret:
        ZOHO_CLIENT_SECRET = args.zoho_secret
    if args.zoho_refresh:
        ZOHO_REFRESH_TOKEN = args.zoho_refresh

    # Log which credentials we're using (only first 5 chars for security)
    logger.info(f"Using RingCentral client ID: {RC_CLIENT_ID[:5]}*** (first 5 chars)")
    logger.info(f"Using Zoho client ID: {ZOHO_CLIENT_ID[:5]}*** (first 5 chars)")

    # Load configurations
    extension_ids, extension_names = load_extensions(args.extensions_file)
    lead_owners = load_lead_owners(args.lead_owners_file)

    # Initialize API clients with rate limiting and token refresh
    rc_client = RingCentralClient(
        RC_JWT_TOKEN, RC_CLIENT_ID, RC_CLIENT_SECRET, RC_ACCOUNT_ID)
    zoho_client = ZohoClient(
        ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REFRESH_TOKEN, dry_run=args.dry_run)

    # Set date range
    if args.start_date and args.end_date:
        start_date, end_date = args.start_date, args.end_date
    else:
        start_date, end_date = get_yesterday_date_range()

    logger.info(f"Processing calls from {start_date} to {end_date}")

    # Get call logs for all extensions with rate limiting
    all_call_logs = []
    for extension_id in extension_ids:
        logger.info(
            f"Getting call logs for extension {extension_id} from {start_date} to {end_date}")
        try:
            call_logs = rc_client.get_call_logs(extension_id, start_date, end_date)
            if call_logs:
                # Debug check for invalid call structures
                for call in call_logs:
                    if not call.get('from') or not call.get('from', {}).get('phoneNumber'):
                        logger.debug(f"Found call with missing from/phoneNumber: {call}")
                        
                all_call_logs.extend(call_logs)
                logger.info(
                    f"Retrieved {len(call_logs)} call logs for extension {extension_id}")
            else:
                logger.info(f"No call logs found for extension {extension_id}")
        except Exception as e:
            logger.error(f"Error getting call logs for extension {extension_id}: {e}")
            continue

    # Process the call logs with rate limiting
    process_accepted_calls(
        all_call_logs, zoho_client, extension_ids, extension_names, lead_owners, rc_client, dry_run=args.dry_run)


if __name__ == "__main__":
    main()