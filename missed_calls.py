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

# Set up logging with date and time in filename
current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(logs_dir, f'missed_calls_{current_time}.log')

# If logger already has handlers, we'll remove them to avoid duplicate logs
if logger.handlers:
    for handler in logger.handlers:
        logger.removeHandler(handler)

# Add new handlers with the timestamped log file
file_handler = logging.FileHandler(log_file)
console_handler = logging.StreamHandler()
formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

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
        """Get missed call logs from RingCentral API for a specific extension."""
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
            'perPage': 250,  # Increased perPage limit
            'result': 'Missed'  # Explicitly filter for missed calls only
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
            logger.info(f"Retrieved {len(records)} missed calls for extension {extension_id}")
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
            
        # Enhanced logging and validation for the lead_owner
        lead_owner_id = None
        
        try:
            # Explicitly check lead_owner structure and the id field
            if not lead_owner:
                logger.error("Lead owner is None")
                return
            
            if not isinstance(lead_owner, dict):
                logger.error(f"Lead owner is not a dictionary: {lead_owner}")
                return
            
            if 'id' not in lead_owner:
                logger.error(f"Lead owner is missing 'id' key: {lead_owner}")
                return
            
            lead_owner_id = lead_owner['id']
            if not lead_owner_id:
                logger.error(f"Lead owner 'id' is empty or None: {lead_owner}")
                return
            
            # Log the lead owner being used
            logger.debug(f"Using lead owner: {lead_owner}")
            logger.debug(f"Lead owner ID: {lead_owner_id}")
            
            phone_number = call['from']['phoneNumber']
            extension_id = call['to'].get('extensionId')
            lead_source = extension_names.get(extension_id, "Unknown")
            lead_status = "Missed Call"  # Set Lead Status to "Missed Call"
            first_name = "Unknown Caller"
            last_name = "Unknown Caller"

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
            
            # Get additional call details for the note
            call_details = []
            call_details.append(f"Call time: {call_time}")
            call_details.append(f"Call direction: {call.get('direction', 'Unknown')}")
            call_details.append(f"Call duration: {call.get('duration', 'Unknown')} seconds")
            call_details.append(f"Caller number: {phone_number}")
            call_details.append(f"Called extension: {extension_names.get(extension_id, extension_id)}")
            call_details.append(f"Call result: {call.get('result', 'Unknown')}")
            
            # Format note content with detailed information
            note_content = "\n".join([
                f"Missed call received on {call_time}",
                "---",
                *call_details,
                "---",
                f"Lead owner: {lead_owner.get('name', lead_owner_id)}",
                f"Call ID: {call.get('id', 'Unknown')}"
            ])

            # Search for existing lead
            existing_lead = self.search_records("Leads", f"Phone:equals:{phone_number}")

            if existing_lead:
                lead_id = existing_lead[0]['id']
                logger.info(f"Existing lead found {lead_id} for {phone_number}. Adding a note.")
                
                # Add note to existing lead with more detailed information
                note_result = self.add_note_to_lead(lead_id, note_content)
                if not note_result:
                    logger.error(f"Failed to add note to existing lead {lead_id}")
                    # Retry once with simplified note content
                    simplified_note = f"Missed call received on {call_time} from {phone_number}."
                    retry_result = self.add_note_to_lead(lead_id, simplified_note)
                    if retry_result:
                        logger.info(f"Successfully added simplified note to lead {lead_id} after retry")
                return lead_id
            else:
                # Build the data payload with the validated lead_owner_id
                data = {
                    "data": [
                        {
                            "Phone": phone_number,
                            "Owner": {"id": lead_owner_id},
                            "Lead_Source": lead_source,
                            "Lead_Status": lead_status,
                            "First_Name": first_name,
                            "Last_Name": last_name,
                            "Description": note_content  # Add call details to the lead description field
                        }
                    ]
                }
                
                # Log the full data payload for debugging
                logger.debug(f"Creating lead with data: {data}")
                
                if self.dry_run:
                    logger.info(f"[DRY-RUN] Would have created lead with data: {data}")
                    return "dry_run_id"
                else:
                    lead_id = self.create_zoho_lead(data)
                    if lead_id:
                        # Add note for new lead creation with more detailed information
                        creation_note = f"New lead created from missed call on {call_time}.\n\n{note_content}"
                        note_result = self.add_note_to_lead(lead_id, creation_note)
                        if not note_result:
                            logger.error(f"Failed to add creation note to new lead {lead_id}")
                            # Retry with simplified note
                            simplified_note = f"New lead created from missed call on {call_time}."
                            retry_result = self.add_note_to_lead(lead_id, simplified_note)
                            if retry_result:
                                logger.info(f"Successfully added simplified note to lead {lead_id} after retry")
                        
                        logger.info(f"Created new lead {lead_id} with note")
                        return lead_id
                    else:
                        logger.error("Failed to create lead - create_zoho_lead returned None")
                    return None
        except Exception as e:
            logger.error(f"Exception in create_or_update_lead: {str(e)}")
            logger.error(f"Lead owner was: {lead_owner}")
            logger.error(f"Call data was: {call}")
            return None

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
        
        if not lead_id:
            logger.error("No lead ID provided for adding note")
            return None

        logger.info(f"Adding note to lead {lead_id}: {note_content}")

        # Set up the request
        url = f"{self.base_url}/Leads/{lead_id}/Notes"
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

        # Log the request details for debugging
        logger.debug(f"Notes API URL: {url}")
        logger.debug(f"Notes API Headers: {headers}")
        logger.debug(f"Notes API Data: {data}")

        try:
            response = requests.post(url, headers=headers, json=data)
            logger.debug(f"Note API response status: {response.status_code}")
            logger.debug(f"Note API response body: {response.text[:500]}")  # Limit response text length
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Successfully added note to lead {lead_id}")
                try:
                    # Check if notes were actually added
                    resp_data = response.json()
                    if resp_data and 'data' in resp_data and len(resp_data['data']) > 0:
                        note_id = resp_data['data'][0].get('details', {}).get('id', None)
                        if note_id:
                            logger.info(f"Created note with ID: {note_id}")
                        else:
                            logger.warning(f"Note created but could not find note ID in response: {resp_data}")
                    else:
                        logger.warning(f"Note API returned success but no data: {resp_data}")
                except Exception as e:
                    logger.warning(f"Error parsing note creation response: {e}")
                return True
            else:
                logger.error(f"Error adding note to lead {lead_id}: {response.status_code} - {response.text}")
                # Try to extract an error message from the response
                try:
                    error_data = response.json()
                    if 'message' in error_data:
                        logger.error(f"API Error: {error_data['message']}")
                except Exception:
                    pass
                return None
        except Exception as e:
            logger.error(f"Exception adding note to lead {lead_id}: {e}")
            return None

    def create_zoho_lead(self, lead_data):
        """Create a new lead in Zoho CRM."""
        if not self.access_token:
            logger.error("No access token available")
            return None

        # Validate lead_data
        if not lead_data or not isinstance(lead_data, dict) or 'data' not in lead_data:
            logger.error(f"Invalid lead data format: {lead_data}")
            return None
        
        # Ensure data is a list and has at least one item
        if not isinstance(lead_data['data'], list) or len(lead_data['data']) == 0:
            logger.error(f"Invalid lead data 'data' field, must be a non-empty list: {lead_data}")
            return None
        
        # Check that the first lead has an Owner with an id
        first_lead = lead_data['data'][0]
        if 'Owner' not in first_lead or not isinstance(first_lead['Owner'], dict) or 'id' not in first_lead['Owner']:
            logger.error(f"Missing or invalid Owner.id in lead data: {first_lead}")
            return None
        
        url = f"{self.base_url}/Leads"
        headers = {
            "Authorization": f"Zoho-oauthtoken {self.access_token}",
            "Content-Type": "application/json"
        }

        logger.debug(f"Creating lead with URL: {url}")
        logger.debug(f"Headers: {headers}")
        logger.debug(f"Data: {lead_data}")

        try:
            response = requests.post(url, headers=headers, json=lead_data)
            
            # Log detailed response information for debugging
            logger.debug(f"API response status: {response.status_code}")
            logger.debug(f"API response headers: {response.headers}")
            logger.debug(f"API response body: {response.text[:1000]}")  # Limit response text length
            
            if response.status_code == 201:
                try:
                    data = response.json()
                    logger.debug(f"Response JSON structure: {data}")
                    
                    if data and 'data' in data and isinstance(data['data'], list) and len(data['data']) > 0:
                        # First check for the new structure (details.id)
                        if 'details' in data['data'][0] and isinstance(data['data'][0]['details'], dict) and 'id' in data['data'][0]['details']:
                            lead_id = data['data'][0]['details']['id']
                            logger.info(f"Successfully created lead {lead_id}")
                            return lead_id
                            
                        # Then try the old structure (direct id)
                        elif 'id' in data['data'][0]:
                            lead_id = data['data'][0]['id']
                            logger.info(f"Successfully created lead {lead_id}")
                            return lead_id
                            
                        else:
                            logger.error("ID not found in expected locations in response")
                            logger.error(f"Full response data: {data}")
                            return None
                    else:
                        logger.error(f"Invalid response data structure: {data}")
                        return None
                except ValueError as e:
                    logger.error(f"Error parsing JSON response: {e}")
                    logger.error(f"Response text: {response.text[:500]}")
                    return None
            else:
                # Decode error response for better logging
                error_message = "Unknown error"
                try:
                    error_data = response.json()
                    if 'message' in error_data:
                        error_message = error_data['message']
                    elif 'error' in error_data:
                        error_message = error_data['error']
                except Exception:
                    error_message = response.text[:200]  # Use part of the raw response if JSON parsing fails
                
                logger.error(f"Error creating lead: HTTP {response.status_code}: {error_message}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception creating lead: {e}")
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
            elif response.status_code == 204:
                # 204 means No Content - successful request but no matching records
                logger.info(f"No records found in Zoho matching criteria: {criteria}")
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
    if config_path:
        config_file = config_path
    else:
        # Get the script directory and use paths relative to it
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(script_dir, 'data', 'extensions.json')
        
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
    if config_path:
        config_file = config_path
    else:
        # Get the script directory and use paths relative to it
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(script_dir, 'data', 'lead_owners.json')
        
    try:
        with open(config_file, 'r') as f:
            lead_owners = json.load(f)
        
        # Validate lead owners structure
        if not lead_owners or not isinstance(lead_owners, list):
            logger.error(f"Invalid lead owners file format: expected a list, got {type(lead_owners)}")
            return []
            
        # Validate each lead owner has required fields
        valid_owners = []
        for i, owner in enumerate(lead_owners):
            if not isinstance(owner, dict):
                logger.error(f"Lead owner at index {i} is not a dictionary: {owner}")
                continue
            if 'id' not in owner:
                logger.error(f"Lead owner at index {i} is missing required 'id' field: {owner}")
                continue
            if 'name' not in owner:
                logger.warning(f"Lead owner at index {i} is missing 'name' field: {owner}")
            if 'email' not in owner:
                logger.warning(f"Lead owner at index {i} is missing 'email' field: {owner}")
            
            valid_owners.append(owner)
            
        if not valid_owners:
            logger.error("No valid lead owners found in configuration")
            return []
            
        logger.info(f"Loaded {len(valid_owners)} lead owners from {config_file}")
        return valid_owners
    except FileNotFoundError:
        logger.error(f"Config file not found: {config_file}")
        return []
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in config file: {config_file}")
        return []
    except Exception as e:
        logger.error(f"Error loading lead owners: {e}")
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

    # Initialize counters for statistics
    stats = {
        'total_calls': len(call_logs),
        'processed_calls': 0,
        'existing_leads': 0,
        'new_leads': 0,
        'skipped_calls': 0,
        'accepted_calls': 0
    }

    # Debugging: Log the lead owners structure to identify any issues
    logger.debug(f"Lead owners structure: {lead_owners}")

    # Ensure lead_owners is a list and each owner has an 'id' key
    if not isinstance(lead_owners, list) or len(lead_owners) == 0:
        logger.error("Invalid lead_owners structure, must be a non-empty list")
        return stats
    
    # Verify each lead owner has the required 'id' field
    for i, owner in enumerate(lead_owners):
        if not isinstance(owner, dict) or 'id' not in owner:
            logger.error(f"Lead owner at index {i} missing 'id' field: {owner}")
            return stats

    # Create a safe round-robin cycle of lead owners
    try:
        owner_cycle = itertools.cycle(lead_owners)
    except Exception as e:
        logger.error(f"Failed to create lead owner cycle: {e}")
        # Create a fallback with a single lead owner
        owner_cycle = itertools.cycle([lead_owners[0]])
        logger.warning(f"Using fallback with single lead owner: {lead_owners[0]}")

    for call in call_logs:
        try:
            # Skip invalid calls
            if not call.get('from') or not call.get('from', {}).get('phoneNumber'):
                logger.warning(f"Call is missing phone number data, skipping: {call.get('id')}")
                stats['skipped_calls'] += 1
                continue

            # Skip calls not for configured extensions
            extension_id = call['to'].get('extensionId')
            if str(extension_id) not in extension_ids:
                logger.warning(f"Skipping call {call.get('id')} - extension {extension_id} not in configured extensions")
                stats['skipped_calls'] += 1
                continue
                
            # Check call result - ONLY process missed calls, skip accepted calls
            call_result = call.get('result', '').lower()
            
            # Log all call results for debugging
            logger.debug(f"Call {call.get('id')} has result: {call_result}")
            
            if call_result != 'missed':
                logger.info(f"Skipping call {call.get('id')} - result is '{call_result}', not 'missed'")
                if call_result == 'accepted':
                    stats['accepted_calls'] += 1
                else:
                    stats['skipped_calls'] += 1
                continue

            # Get the caller's phone number
            phone_number = call['from']['phoneNumber']

            # Check if this is an existing lead
            existing_lead = zoho_client.search_records("Leads", f"Phone:equals:{phone_number}")
            if existing_lead:
                stats['existing_leads'] += 1
            else:
                stats['new_leads'] += 1

            # Get the next lead owner in the cycle - with explicit exception handling
            try:
                lead_owner = next(owner_cycle)
                logger.debug(f"Assigned lead owner: {lead_owner}")
            except Exception as e:
                logger.error(f"Error getting next lead owner: {e}")
                # Use the first lead owner as a fallback
                lead_owner = lead_owners[0]
                logger.warning(f"Using fallback lead owner: {lead_owner}")

            # Create or update the lead
            zoho_client.create_or_update_lead(call, lead_owner, extension_names)
            stats['processed_calls'] += 1
            
        except Exception as e:
            logger.error(f"Error processing call {call.get('id', 'unknown')}: {e}")
            stats['skipped_calls'] += 1
            continue

    # Log and return statistics
    logger.info(f"Call Processing Summary:")
    logger.info(f"  Total calls found: {stats['total_calls']}")
    logger.info(f"  Calls processed (missed): {stats['processed_calls']}")
    logger.info(f"  Calls skipped (accepted): {stats['accepted_calls']}")
    logger.info(f"  Other calls skipped: {stats['skipped_calls']}")
    logger.info(f"  Existing leads updated: {stats['existing_leads']}")
    logger.info(f"  New leads created: {stats['new_leads'] if not dry_run else '0 (dry run)'}")
    
    return stats


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Process missed calls from RingCentral and create leads in Zoho CRM.')
    parser.add_argument(
        '--start-date', help='Start date for call logs (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date for call logs (YYYY-MM-DD)')
    parser.add_argument('--hours-back', type=int, help='Process calls from the last N hours')
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
        
        # Set up logging
        logger = setup_logging("missed_calls")
        if args.debug:
            logger.setLevel(logging.DEBUG)
        
        # Get date range for processing
        if args.start_date and args.end_date:
            # Convert space to 'T' in the datetime strings
            start_date = args.start_date.replace(" ", "T")
            end_date = args.end_date.replace(" ", "T")
        elif args.hours_back:
            end_date = datetime.now()
            start_date = end_date - timedelta(hours=args.hours_back)
            start_date = start_date.strftime("%Y-%m-%dT%H:%M:%S")
            end_date = end_date.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            # Default to last 24 hours
            end_date = datetime.now()
            start_date = end_date - timedelta(hours=24)
            start_date = start_date.strftime("%Y-%m-%dT%H:%M:%S")
            end_date = end_date.strftime("%Y-%m-%dT%H:%M:%S")
            
        logger.info(f"Processing MISSED calls from {start_date} to {end_date}")
        logger.info("NOTE: Only calls with result='missed' will be processed. Accepted calls will be skipped.")
        
        # Initialize clients
        rc_client = RingCentralClient()
        zoho_client = ZohoClient(dry_run=args.dry_run)
        
        # Load configuration
        extension_ids, extension_names = load_extensions()
        if not extension_ids:
            logger.error("No extensions configured. Please configure extensions before running this script.")
            return
            
        lead_owners = load_lead_owners()
        if not lead_owners:
            if args.dry_run:
                # In dry run mode, we can create a dummy lead owner for testing
                logger.warning("No lead owners configured. Creating a dummy lead owner for dry run.")
                lead_owners = [{
                    "id": "dummy_id_12345",
                    "name": "Dummy Lead Owner",
                    "email": "dummy@example.com"
                }]
            else:
                logger.error("No lead owners configured. Please configure lead owners before running this script.")
                return
        
        # Log information about the loaded configuration
        logger.info(f"Found {len(extension_ids)} configured extensions")
        logger.info(f"Found {len(lead_owners)} configured lead owners")
            
        # Process call logs for each extension
        all_call_logs = []
        for extension_id in extension_ids:
            extension_name = extension_names.get(extension_id, "Unknown")
            logger.info(f"Retrieving missed calls for extension {extension_name}")
            call_logs = rc_client.get_call_logs(extension_id, start_date, end_date)
            if call_logs:
                all_call_logs.extend(call_logs)
         
        # Process all the call logs and get statistics   
        stats = process_missed_calls(all_call_logs, zoho_client, extension_ids, extension_names, lead_owners, args.dry_run)
            
        logger.info("Processing completed successfully")
        
        # Log a summary of results
        if stats:
            mode = "DRY RUN" if args.dry_run else "PRODUCTION"
            logger.info(f"FINAL SUMMARY ({mode}):")
            logger.info(f"  Date range: {start_date} to {end_date}")
            logger.info(f"  Total extensions processed: {len(extension_ids)}")
            logger.info(f"  Total calls found: {stats['total_calls']}")
            logger.info(f"  Missed calls processed: {stats['processed_calls']}")
            logger.info(f"  Existing leads updated: {stats['existing_leads']}")
            logger.info(f"  New leads created: {stats['new_leads'] if not args.dry_run else '0 (dry run)'}")
            logger.info(f"  Accepted calls skipped: {stats.get('accepted_calls', 0)}")
            logger.info(f"  Other calls skipped: {stats.get('skipped_calls', 0)}")
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        raise


if __name__ == "__main__":
    main()