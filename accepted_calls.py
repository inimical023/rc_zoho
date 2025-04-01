from common import *   # Now you have os, sys, json, logging, etc.
import itertools  # For round-robin lead owner assignment
import argparse
import time  # Add explicit import for time module
import subprocess
import sys
import pkg_resources
from datetime import datetime, timedelta
import base64
import requests

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

# Set up logging with date and time in filename
current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(logs_dir, f'accepted_calls_{current_time}.log')

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("accepted_calls")


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

    def _refresh_access_token(self):
        """Refresh the OAuth access token using JWT."""
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
        
        max_retries = 3
        backoff_factor = 2
        delay = 1
        
        for attempt in range(max_retries):
            try:
                response = requests.post(url, headers=headers, data=data)
                response.raise_for_status()
                token_data = response.json()
                self.access_token = token_data["access_token"]
                logger.info(f"RingCentral token refreshed successfully. Expires in {token_data.get('expires_in', 'unknown')} seconds")
                return True
            except Exception as e:
                logger.warning(f"Error refreshing RingCentral token (attempt {attempt+1}/{max_retries}): {str(e)}")
                time.sleep(delay)
                delay *= backoff_factor
        
        logger.error("Failed to refresh RingCentral token after multiple attempts")
        raise Exception("Failed to refresh RingCentral token")

    def get_call_logs(self, extension_id, start_date=None, end_date=None):
        """Get call logs from RingCentral API for a specific extension."""
        if not self.access_token:
            self._refresh_access_token()

        url = f"{self.base_url}/restapi/v1.0/account/{self.account_id}/extension/{extension_id}/call-log"
        params = {
            'direction': 'Inbound',
            'type': 'Voice',
            'view': 'Detailed',
            'withRecording': 'true',  # Include recording info
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

        # Handle pagination and API rate limits
        all_records = []
        page = 1
        
        while True:
            try:
                params['page'] = page
                response = requests.get(url, headers=headers, params=params)
                
                if response.status_code == 401:  # Unauthorized - token expired
                    logger.warning("Access token expired, refreshing...")
                    self._refresh_access_token()
                    headers['Authorization'] = f'Bearer {self.access_token}'
                    continue  # Retry with new token
                    
                if response.status_code == 429:  # Rate limit
                    retry_after = int(response.headers.get('Retry-After', 10))
                    logger.warning(f"Rate limit hit, retrying after {retry_after} seconds")
                    time.sleep(retry_after)
                    continue
                    
                response.raise_for_status()
                data = response.json()
                records = data.get('records', [])
                
                if not records:
                    break  # No more records
                    
                all_records.extend(records)
                
                # Check if there are more pages
                navigation = data.get('navigation', {})
                if page >= navigation.get('totalPages', 1):
                    break
                    
                page += 1
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error getting call logs for extension {extension_id}: {str(e)}")
                if page > 1:  # Return what we've collected so far if we got something
                    break
                return []
        
        logger.info(f"Retrieved {len(all_records)} total call logs for extension {extension_id}")
        return all_records

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
        
        max_retries = 3
        backoff_factor = 2
        delay = 1
        
        for attempt in range(max_retries):
            try:
                response = requests.post(url, data=data)
                response.raise_for_status()
                token_data = response.json()
                self.access_token = token_data["access_token"]
                logger.debug(f"Zoho authentication successful. Token expires in {token_data.get('expires_in', 'unknown')} seconds")
                return True
            except Exception as e:
                logger.warning(f"Error refreshing Zoho token (attempt {attempt+1}/{max_retries}): {str(e)}")
                time.sleep(delay)
                delay *= backoff_factor
                
        logger.error("Failed to refresh Zoho token after multiple attempts")
        raise Exception("Failed to refresh Zoho token")
        
    def _ensure_valid_token(self):
        """Ensure we have a valid access token before making API calls."""
        if not self.access_token:
            self._get_access_token()

    def is_recording_already_attached(self, lead_id, recording_id):
        """Check if a recording is already attached to a lead in Zoho CRM."""
        self._ensure_valid_token()
        
        url = f"{self.base_url}/Leads/{lead_id}/Attachments"
        headers = {
            "Authorization": f"Zoho-oauthtoken {self.access_token}",
        }
        params = {
            "fields": "id,File_Name"  # Add the required fields parameter
        }
    
        try:
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 401:  # Token expired
                self._get_access_token()
                headers = {"Authorization": f"Zoho-oauthtoken {self.access_token}"}
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
        self._ensure_valid_token()
        
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
                
                # Determine file extension based on content type
                if content_type == "audio/mpeg":
                    extension = "mp3"
                elif content_type == "audio/wav":
                    extension = "wav"
                else:
                    extension = content_type.split('/')[1] if '/' in content_type else "bin"
                
                # Create the filename with the formatted call time
                filename = f"{formatted_call_time}_recording_{recording_id}.{extension}"
                files = {
                    # Set filename and content type
                    'file': (filename, recording_content, content_type)
                }
    
                try:
                    response = requests.post(url, headers=headers, files=files)
                    
                    if response.status_code == 401:  # Token expired
                        self._get_access_token()
                        headers = {"Authorization": f"Zoho-oauthtoken {self.access_token}"}
                        response = requests.post(url, headers=headers, files=files)
    
                    if response.status_code in [200, 201, 202]:
                        logger.info(f"Successfully attached recording {recording_id} to lead {lead_id}")
                        return True
                    else:
                        logger.error(
                            f"Error attaching recording {recording_id} to lead {lead_id}. Status code: {response.status_code}, Response: {response.text}")
                        # Add a note about the failed recording attachment
                        self.add_note_to_lead(lead_id, f"Failed to attach recording {recording_id} at {call_time.strftime('%Y-%m-%d %H:%M:%S')}. Error: {response.status_code}")
                        return False
    
                except Exception as e:
                    logger.error(f"Exception attaching recording {recording_id} to lead {lead_id}: {e}")
                    # Add a note about the failed recording attachment
                    self.add_note_to_lead(lead_id, f"Failed to attach recording {recording_id} at {call_time.strftime('%Y-%m-%d %H:%M:%S')}. Error: {str(e)}")
                    return False
            else:
                logger.warning(f"Could not retrieve recording content for recording ID: {recording_id}")
                # Add a note about the unavailable recording content
                self.add_note_to_lead(lead_id, f"Recording {recording_id} at {call_time.strftime('%Y-%m-%d %H:%M:%S')} could not be retrieved.")
                return False
        else:
            logger.info("No recording ID found for this call.")
            # Add a note that no recording was available for this call
            self.add_note_to_lead(lead_id, f"No recording was available for call at {call_time.strftime('%Y-%m-%d %H:%M:%S')}.")
            return True

    def create_zoho_lead(self, lead_data):
        """Create a new lead in Zoho CRM."""
        self._ensure_valid_token()

        url = f"{self.base_url}/Leads"
        headers = {
            "Authorization": f"Zoho-oauthtoken {self.access_token}",
            "Content-Type": "application/json"
        }

        # Log what we're about to send
        logger.debug(f"Creating lead with data: {lead_data}")
        
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would have created lead with data: {lead_data}")
            return "dry_run_lead_id"

        try:
            response = requests.post(url, headers=headers, json=lead_data)
            
            if response.status_code == 401:  # Token expired
                self._get_access_token()
                headers = {"Authorization": f"Zoho-oauthtoken {self.access_token}"}
                response = requests.post(url, headers=headers, json=lead_data)
                
            if response.status_code == 201:
                data = response.json()
                logger.debug(f"Lead creation response: {data}")
                
                if data and 'data' in data and data['data']:
                    # Check both possible structures
                    if 'details' in data['data'][0] and 'id' in data['data'][0]['details']:
                        lead_id = data['data'][0]['details']['id']
                    elif 'id' in data['data'][0]:
                        lead_id = data['data'][0]['id']
                    else:
                        logger.error("Could not find lead ID in response")
                        return None
                        
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
        self._ensure_valid_token()

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
            
            if response.status_code == 401:  # Token expired
                self._get_access_token()
                headers = {"Authorization": f"Zoho-oauthtoken {self.access_token}"}
                response = requests.get(url, headers=headers, params=params)
                
            if response.status_code == 200:
                data = response.json()
                if data and 'data' in data and data['data']:
                    return data['data']
                else:
                    logger.info(f"No records found matching criteria: {criteria}")
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

    def update_lead_status(self, lead_id, status):
        """Update a lead's status in Zoho CRM."""
        self._ensure_valid_token()
        
        url = f"{self.base_url}/Leads"
        headers = {
            "Authorization": f"Zoho-oauthtoken {self.access_token}",
            "Content-Type": "application/json"
        }
        data = {
            "data": [
                {
                    "id": lead_id,
                    "Lead_Status": status
                }
            ]
        }
        
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would update lead {lead_id} status to '{status}'")
            return True
            
        try:
            response = requests.put(url, headers=headers, json=data)
            
            if response.status_code == 401:  # Token expired
                self._get_access_token()
                headers = {"Authorization": f"Zoho-oauthtoken {self.access_token}"}
                response = requests.put(url, headers=headers, json=data)
                
            if response.status_code in [200, 202]:
                logger.info(f"Successfully updated lead {lead_id} status to '{status}'")
                return True
            else:
                logger.error(f"Error updating lead status: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Exception updating lead status: {str(e)}")
            return False

    def add_note_to_lead(self, lead_id, note_content):
        """Add a note to a lead in Zoho CRM."""
        self._ensure_valid_token()
        
        if not lead_id:
            logger.error("Cannot add note: No lead ID provided")
            return False
            
        if self.dry_run:
            logger.info(f"[DRY-RUN] Would add note to lead {lead_id}: {note_content}")
            return True

        url = f"{self.base_url}/Leads/{lead_id}/Notes"
        headers = {
            "Authorization": f"Zoho-oauthtoken {self.access_token}",
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
            
            if response.status_code == 401:  # Token expired
                self._get_access_token()
                headers = {"Authorization": f"Zoho-oauthtoken {self.access_token}"}
                response = requests.post(url, headers=headers, json=data)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"Successfully added note to lead {lead_id}")
                return True
            else:
                logger.error(f"Error adding note to lead {lead_id}. Status code: {response.status_code}, Response: {response.text}")
                
                # Try a simplified note if it fails
                if len(note_content) > 1000:
                    simplified_note = note_content[:997] + "..."
                    logger.info(f"Retrying with simplified note")
                    return self.add_note_to_lead(lead_id, simplified_note)
                return False
                
        except Exception as e:
            logger.error(f"Exception adding note to lead {lead_id}: {e}")
            return False

    def create_or_update_lead(self, call, lead_owner, extension_names, rc_client):
        """Create or update a lead in Zoho CRM based on call information."""
        self._ensure_valid_token()
        
        # Check if call has the required structure
        if not call.get('from') or not call.get('from', {}).get('phoneNumber'):
            logger.warning(f"Call {call.get('id')} is missing phone number data, skipping")
            return None
            
        phone_number = call['from']['phoneNumber']
        extension_id = call['to'].get('extensionId')
        lead_source = extension_names.get(str(extension_id), "Unknown")
        lead_status = "Accepted Call No Lead Created"  # Set Lead Status to "Accepted Call No Lead Created"
        first_name = "Unknown"
        last_name = "Caller"

        # Extract call receive time from RingCentral API
        call_time = None
        try:
            call_time = datetime.fromisoformat(call.get('startTime', '').replace('Z', '+00:00'))
            formatted_time = call_time.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            call_time = datetime.now()
            formatted_time = call_time.strftime("%Y-%m-%d %H:%M:%S")
            logger.warning(f"Could not parse call time for call {call.get('id')}, using current time")

        # Prepare detailed call information for notes
        call_details = []
        call_details.append(f"Call time: {formatted_time}")
        call_details.append(f"Call direction: {call.get('direction', 'Unknown')}")
        call_details.append(f"Call duration: {call.get('duration', 'Unknown')} seconds")
        call_details.append(f"Caller number: {phone_number}")
        call_details.append(f"Called extension: {extension_names.get(str(extension_id), extension_id)}")
        call_details.append(f"Call result: {call.get('result', 'Unknown')}")
        call_details.append(f"Call ID: {call.get('id', 'Unknown')}")
        
        # Format note content with detailed information
        note_content = "\n".join([
            f"Accepted call received on {formatted_time}",
            "---",
            *call_details,
            "---",
            f"Lead owner: {lead_owner.get('name', 'Unknown') if lead_owner else 'Unknown'}"
        ])

        # Search for an existing lead by phone number
        existing_lead = self.search_records("Leads", f"Phone:equals:{phone_number}")

        if existing_lead:
            # Update the existing lead
            lead_id = existing_lead[0]['id']
            logger.info(f"Found existing lead {lead_id} for phone number {phone_number}")
            
            # Update lead status to "Accepted Call"
            self.update_lead_status(lead_id, lead_status)
            
            # Add detailed note about this accepted call
            self.add_note_to_lead(lead_id, note_content)
            
            # Attach recording to the existing lead if one exists
            if not self.dry_run:
                self.attach_recording_to_lead(call, lead_id, rc_client, call_time)
                
            return lead_id
            
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
                        "Description": f"Lead created from accepted call received on {formatted_time}"
                    }
                ]
            }
            
            # Add owner if available
            if lead_owner and lead_owner.get('id'):
                lead_data['data'][0]['Owner'] = {"id": lead_owner.get('id')}
                
            # Create the lead
            lead_id = self.create_zoho_lead(lead_data)
            
            if lead_id:
                # Add detailed creation note
                creation_note = f"New lead created from accepted call on {formatted_time}.\n\n{note_content}"
                self.add_note_to_lead(lead_id, creation_note)
                
                # Attach recording if one exists
                if not self.dry_run:
                    self.attach_recording_to_lead(call, lead_id, rc_client, call_time)
                    
                return lead_id
            else:
                logger.error(f"Failed to create lead for call {call.get('id')}")
                return None

def get_date_range(hours_back=None, start_date=None, end_date=None):
    """Get date range based on input parameters."""
    if start_date and end_date:
        # Convert space to 'T' in the datetime strings if needed
        start_date = start_date.replace(" ", "T") if " " in start_date else start_date
        end_date = end_date.replace(" ", "T") if " " in end_date else end_date
        return start_date, end_date
    elif hours_back:
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=hours_back)
        return start_date.strftime("%Y-%m-%dT%H:%M:%S"), end_date.strftime("%Y-%m-%dT%H:%M:%S")
    else:
        # Default to last 24 hours
        end_date = datetime.now()
        start_date = end_date - timedelta(hours=24)
        return start_date.strftime("%Y-%m-%dT%H:%M:%S"), end_date.strftime("%Y-%m-%dT%H:%M:%S")

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
                    logger.info(f"Call ID {call.get('id')}, Leg to.name: {leg_to_name}")
            elif leg_to_extension_id:
                extension_name = extension_names.get(str(leg_to_extension_id))
                return True, {'details': {'extension_name': extension_name}}
            else:
                return False, {'reason': 'No lead owner found for accepted call'}

    return False, {'reason': 'No leg with \'Accepted\' result and a lead owner name'}

def process_accepted_calls(call_logs, zoho_client, extension_ids, extension_names, lead_owners, rc_client, dry_run=False):
    """Process accepted calls and create leads in Zoho CRM."""
    if not call_logs:
        logger.warning("No call logs to process")
        return

    # Initialize statistics
    stats = {
        'total_calls': len(call_logs),
        'qualified_calls': 0,
        'processed_calls': 0,
        'existing_leads': 0,
        'new_leads': 0,
        'skipped_calls': 0,
        'recordings_attached': 0,
        'recording_failures': 0
    }

    # Create a round-robin iterator for lead owners
    lead_owner_cycle = itertools.cycle(lead_owners)
    
    for call in call_logs:
        # Skip invalid calls
        if not call.get('from') or not call.get('from', {}).get('phoneNumber'):
            logger.warning(f"Call has invalid structure, skipping: {call.get('id')}")
            stats['skipped_calls'] += 1
            continue
            
        # Qualify the call
        is_qualified, decision_data = qualify_call(call, extension_names, lead_owners)
        
        if is_qualified:
            stats['qualified_calls'] += 1
            
            # Extract lead owner information
            if 'lead_owner' in decision_data.get('details', {}):
                lead_owner_name = decision_data['details']['lead_owner']['name']
                lead_owner_id = decision_data['details']['lead_owner']['id']
                lead_owner = decision_data['details']['lead_owner']
            elif 'extension_name' in decision_data.get('details', {}):
                lead_owner_name = decision_data['details']['extension_name']
                lead_owner_id = None  # No lead owner ID in this case
                lead_owner = next(lead_owner_cycle)  # Use next owner in round-robin cycle
            else:
                logger.warning(f"No lead owner information found for call {call.get('id')}")
                lead_owner = next(lead_owner_cycle)  # Use next owner in round-robin cycle
                lead_owner_name = lead_owner.get('name', 'Unknown')

            # Check if call has recording
            has_recording = bool('recording' in call and call['recording'] and 'id' in call['recording'])
            
            # Create or update lead in Zoho
            phone_number = call['from']['phoneNumber']
            existing_lead = zoho_client.search_records("Leads", f"Phone:equals:{phone_number}")
            
            if existing_lead:
                stats['existing_leads'] += 1
            else:
                stats['new_leads'] += 1
                
            lead_id = zoho_client.create_or_update_lead(call, lead_owner, extension_names, rc_client)
            
            if lead_id:
                stats['processed_calls'] += 1
                logger.info(f"Processed call {call.get('id')} - Lead Owner: {lead_owner_name}, Lead ID: {lead_id}")
                
                # Track recording statistics
                if has_recording:
                    if not dry_run and call.get('recording', {}).get('id'):
                        # Statistics will be updated inside the create_or_update_lead method
                        stats['recordings_attached'] += 1
            else:
                logger.warning(f"Failed to process call {call.get('id')}")
                stats['skipped_calls'] += 1
        else:
            reason = decision_data.get('reason', 'Unknown reason')
            logger.info(f"Skipped call {call.get('id')} - Not qualified: {reason}")
            stats['skipped_calls'] += 1
            
        # Add a small delay between processing calls to respect rate limits
        time.sleep(0.5)
    
    # Log statistics
    logger.info(f"Call Processing Summary:")
    logger.info(f"  Total calls found: {stats['total_calls']}")
    logger.info(f"  Calls qualified as 'accepted': {stats['qualified_calls']}")
    logger.info(f"  Calls processed: {stats['processed_calls']}")
    logger.info(f"  Existing leads updated: {stats['existing_leads']}")
    logger.info(f"  New leads created: {stats['new_leads'] if not dry_run else '0 (dry run)'}")
    logger.info(f"  Calls skipped: {stats['skipped_calls']}")
    logger.info(f"  Recordings attached: {stats['recordings_attached'] if not dry_run else '0 (dry run)'}")

    return stats

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Process accepted calls with recordings from RingCentral and create leads in Zoho CRM.')
    parser.add_argument(
        '--start-date', help='Start date for call logs (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--end-date', help='End date for call logs (YYYY-MM-DD HH:MM:SS)')
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
    """Main function"""
    # Set up a default logger in case of early failure
    default_logger = logging.getLogger("accepted_calls")
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Set up logging based on debug flag
        if args.debug:
            logger.setLevel(logging.DEBUG)
            logger.debug("Debug logging enabled")
        else:
            logger.setLevel(logging.INFO)
        
        # Override log file location if provided
        if args.log_file:
            for handler in logger.handlers[:]:
                if isinstance(handler, logging.FileHandler):
                    logger.removeHandler(handler)
            file_handler = logging.FileHandler(args.log_file)
            file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
            logger.addHandler(file_handler)
            logger.info(f"Logging to custom log file: {args.log_file}")
            
        # Display script mode and version
        mode = "DRY RUN" if args.dry_run else "PRODUCTION"
        logger.info(f"Starting accepted calls processing in {mode} mode")
        logger.info(f"AcceptedCalls.py - Starting at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Get date range for processing
        start_date, end_date = get_date_range(args.hours_back, args.start_date, args.end_date)
        logger.info(f"Processing calls from {start_date} to {end_date}")
        
        # Initialize clients
        logger.info("Initializing API clients...")
        try:
            rc_client = RingCentralClient()
            logger.info("RingCentral client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize RingCentral client: {str(e)}")
            return 1
            
        try:
            zoho_client = ZohoClient(dry_run=args.dry_run)
            logger.info("Zoho client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Zoho client: {str(e)}")
            return 1
        
        # Load extensions and lead owners
        extensions = storage.load_extensions()
        lead_owners = storage.load_lead_owners()
        
        if not extensions:
            logger.error("No extensions configured")
            return 1
            
        if not lead_owners:
            logger.error("No lead owners configured")
            return 1
            
        # Create extension mapping
        extension_ids = {str(ext['id']) for ext in extensions}
        extension_names = {str(ext['id']): ext['name'] for ext in extensions}
        
        # Initialize overall statistics
        overall_stats = {
            'total_calls': 0,
            'qualified_calls': 0,
            'processed_calls': 0,
            'existing_leads': 0,
            'new_leads': 0,
            'skipped_calls': 0,
            'recordings_attached': 0,
            'recording_failures': 0
        }
        
        # Process each extension
        logger.info(f"Processing calls for {len(extensions)} extensions")
        all_call_logs = []
        
        for extension in extensions:
            ext_id = extension['id']
            ext_name = extension['name']
            logger.info(f"Getting call logs for extension {ext_name} (ID: {ext_id})")
            
            try:
                call_logs = rc_client.get_call_logs(ext_id, start_date, end_date)
                if call_logs:
                    all_call_logs.extend(call_logs)
                    logger.info(f"Retrieved {len(call_logs)} call logs for extension {ext_name}")
                else:
                    logger.info(f"No call logs found for extension {ext_name}")
            except Exception as e:
                logger.error(f"Error getting call logs for extension {ext_name}: {str(e)}")
                continue
        
        # Process all the call logs together
        logger.info(f"Processing {len(all_call_logs)} total call logs")
        stats = process_accepted_calls(all_call_logs, zoho_client, extension_ids, extension_names, lead_owners, rc_client, args.dry_run)
        
        # Combine statistics
        if stats:
            for key in overall_stats:
                if key in stats:
                    overall_stats[key] = stats[key]
        
        # Log final summary
        logger.info(f"FINAL SUMMARY ({mode}):")
        logger.info(f"  Date range: {start_date} to {end_date}")
        logger.info(f"  Total extensions processed: {len(extensions)}")
        logger.info(f"  Total calls found: {overall_stats['total_calls']}")
        logger.info(f"  Calls qualified as 'accepted': {overall_stats['qualified_calls']}")
        logger.info(f"  Total calls processed: {overall_stats['processed_calls']}")
        logger.info(f"  Existing leads updated: {overall_stats['existing_leads']}")
        logger.info(f"  New leads created: {overall_stats['new_leads'] if not args.dry_run else '0 (dry run)'}")
        logger.info(f"  Calls skipped: {overall_stats['skipped_calls']}")
        logger.info(f"  Recordings attached: {overall_stats['recordings_attached'] if not args.dry_run else '0 (dry run)'}")
        
        logger.info(f"AcceptedCalls.py - Completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("Processing completed successfully")
        
        return 0
        
    except Exception as e:
        # Use the logger if it was created, otherwise use the default logger
        log = logger if 'logger' in locals() else default_logger
        log.error(f"Error in main: {str(e)}")
        log.debug("Stack trace:", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())