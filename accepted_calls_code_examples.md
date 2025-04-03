# AcceptedCalls.py Implementation Code Examples

This document provides specific code examples and implementation details for key components of the `accepted_calls.py` script based on the requirements.

## 1. Call Qualification Logic

The most important missing piece in the current implementation is proper call qualification. Here's how to implement it:

```python
def qualify_call(call):
    """Determine if a call should be qualified as 'accepted' based on call legs.
    A call is considered accepted if at least one leg has a result of 'Accepted'.
    """
    # Skip calls marked as spam
    if call.get('spam', False):
        logger.debug(f"Call {call.get('id')} marked as spam, skipping")
        return False
        
    # Check if call was blocked
    if call.get('blocked', False):
        logger.debug(f"Call {call.get('id')} was blocked, skipping")
        return False
    
    # Check call legs (if available)
    legs = call.get('legs', [])
    if not legs:
        logger.debug(f"Call {call.get('id')} has no legs data, cannot determine status")
        return False
    
    # Look for accepted legs
    for leg in legs:
        # Check result field (primary indicator)
        if leg.get('result') == 'Accepted':
            # Verify telephony status indicates a connected call
            telephony_status = leg.get('telephonyStatus')
            if telephony_status in ['CallConnected', 'Answered', 'HoldOn', 'HoldOff']:
                logger.debug(f"Call {call.get('id')} has accepted leg with connected telephony status")
                return True
    
    logger.debug(f"Call {call.get('id')} has no accepted legs")
    return False
```

## 2. API-Level Filtering for Efficiency

Update the `get_call_logs` method in the `RingCentralClient` class for efficient filtering:

```python
def get_call_logs(self, extension_id, start_date=None, end_date=None):
    """Get call logs from RingCentral API for a specific extension."""
    if not self.access_token:
        self._refresh_access_token()  # Try refreshing if needed

    url = f"{self.base_url}/restapi/v1.0/account/{self.account_id}/extension/{extension_id}/call-log"
    params = {
        'direction': 'Inbound',
        'type': 'Voice',
        'view': 'Detailed',
        'withRecording': 'true',  # Include recording info
        'perPage': 250  # Increased for efficiency
    }

    if start_date:
        params['dateFrom'] = start_date
    if end_date:
        params['dateTo'] = end_date

    headers = {
        'Authorization': f'Bearer {self.access_token}',
        'Content-Type': 'application/json'
    }

    # Handle pagination
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
                return all_records
            return []
    
    # Now filter only accepted calls
    accepted_calls = [call for call in all_records if qualify_call(call)]
    logger.info(f"Found {len(accepted_calls)} accepted calls out of {len(all_records)} total calls")
    return accepted_calls
```

## 3. Token Refresh Implementation

Add token refresh capabilities to the RingCentralClient:

```python
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
```

Implement similar logic for the ZohoClient:

```python
def _refresh_access_token(self):
    """Get a new access token using refresh token."""
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
            logger.info(f"Zoho token refreshed successfully. Expires in {token_data.get('expires_in', 'unknown')} seconds")
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
        self._refresh_access_token()
```

## 4. Improved Recording Attachment Process

Enhance the recording attachment process:

```python
def attach_recording_to_lead(self, call, lead_id, rc_client, call_time):
    """Attach a recording to a lead in Zoho CRM, or add a note if no recording exists."""
    # Ensure valid token
    self._ensure_valid_token()
    
    if 'recording' in call and call['recording'] and 'id' in call['recording']:
        recording_id = call['recording']['id']
        logger.info(f"Processing recording {recording_id} for lead {lead_id}")
        
        # Check if already attached
        if self.is_recording_already_attached(lead_id, recording_id):
            logger.info(f"Recording {recording_id} already attached to lead {lead_id}, skipping")
            return

        # Format filename with timestamp
        timestamp = call_time.strftime("%Y%m%d_%H%M%S")
        
        # Implement rate limiting with exponential backoff
        max_retries = 5
        backoff_factor = 2
        delay = 1
        
        for attempt in range(max_retries):
            try:
                # Get recording content
                recording_content, content_type = rc_client.get_recording_content(recording_id)
                if not recording_content:
                    logger.warning(f"No content retrieved for recording {recording_id}")
                    self.add_note_to_lead(lead_id, f"Recording {recording_id} could not be retrieved (attempt {attempt+1}/{max_retries})")
                    break
                
                # Determine file extension based on content type
                if content_type == "audio/mpeg":
                    extension = "mp3"
                elif content_type == "audio/wav":
                    extension = "wav"
                else:
                    extension = content_type.split('/')[1] if '/' in content_type else "bin"
                
                # Create filename with timestamp
                filename = f"{timestamp}_recording_{recording_id}.{extension}"
                
                # Attach to Zoho lead
                url = f"{self.base_url}/Leads/{lead_id}/Attachments"
                headers = {"Authorization": f"Zoho-oauthtoken {self.access_token}"}
                files = {'file': (filename, recording_content, content_type)}
                
                response = requests.post(url, headers=headers, files=files)
                
                if response.status_code in [200, 201, 202]:
                    logger.info(f"Successfully attached recording {recording_id} to lead {lead_id}")
                    return True
                elif response.status_code == 401:  # Token expired
                    self._refresh_access_token()
                    headers = {"Authorization": f"Zoho-oauthtoken {self.access_token}"}
                    continue  # Retry with new token
                else:
                    logger.error(f"Error attaching recording: {response.status_code} - {response.text}")
                    time.sleep(delay)
                    delay *= backoff_factor
                    
            except Exception as e:
                logger.error(f"Exception attaching recording {recording_id}: {str(e)}")
                time.sleep(delay)
                delay *= backoff_factor
        
        # If we get here, all attempts failed
        self.add_note_to_lead(lead_id, f"Failed to attach recording {recording_id} after {max_retries} attempts")
        return False
    else:
        # No recording available
        self.add_note_to_lead(lead_id, f"No recording was available for call at {call_time.strftime('%Y-%m-%d %H:%M:%S')}")
        return False
```

## 5. Enhanced Lead Creation Process

Improve the lead creation process with more robust error handling:

```python
def create_or_update_lead(self, call, lead_owner, extension_names):
    """Create or update a lead in Zoho CRM based on call information."""
    # Ensure valid token
    self._ensure_valid_token()
    
    # Extract phone number and verify
    if not call.get('from') or not call.get('from', {}).get('phoneNumber'):
        logger.warning(f"Call {call.get('id')} missing phone number, skipping")
        return None
        
    phone_number = call['from']['phoneNumber']
    extension_id = call['to'].get('extensionId')
    lead_source = extension_names.get(str(extension_id), "Unknown Extension")
    
    # Get call time
    try:
        call_time = datetime.fromisoformat(call.get('startTime', '').replace('Z', '+00:00'))
        formatted_time = call_time.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        call_time = datetime.now()
        formatted_time = call_time.strftime("%Y-%m-%d %H:%M:%S")
        logger.warning(f"Could not parse call time for call {call.get('id')}, using current time")
    
    # Check for existing lead
    try:
        existing_lead = self.search_records("Leads", f"Phone:equals:{phone_number}")
        
        if existing_lead:
            # Update existing lead
            lead_id = existing_lead[0]['id']
            logger.info(f"Found existing lead {lead_id} for phone {phone_number}")
            
            # Create a detailed note
            call_duration = call.get('duration', 0)
            duration_str = f"{call_duration} seconds" if call_duration else "unknown duration"
            note_content = (
                f"Accepted call received on {formatted_time}\n"
                f"Duration: {duration_str}\n"
                f"Extension: {lead_source} ({extension_id})\n"
                f"Call ID: {call.get('id', 'Unknown')}"
            )
            
            # Update lead status
            self.update_lead_status(lead_id, "Accepted Call")
            
            # Add note
            self.add_note_to_lead(lead_id, note_content)
            return lead_id
            
        else:
            # Create new lead
            lead_owner_id = lead_owner['id']
            first_name = "Unknown"
            last_name = "Caller"
            
            # Prepare lead data
            lead_data = {
                "data": [
                    {
                        "Phone": phone_number,
                        "Owner": {"id": lead_owner_id},
                        "Lead_Source": lead_source,
                        "Lead_Status": "Accepted Call",
                        "First_Name": first_name,
                        "Last_Name": last_name,
                        "Description": f"Lead created from accepted call received on {formatted_time}"
                    }
                ]
            }
            
            # Create the lead
            lead_id = self.create_zoho_lead(lead_data)
            
            if lead_id:
                # Add note with call details
                call_duration = call.get('duration', 0)
                duration_str = f"{call_duration} seconds" if call_duration else "unknown duration"
                note_content = (
                    f"New lead created from accepted call received on {formatted_time}\n"
                    f"Duration: {duration_str}\n"
                    f"Extension: {lead_source} ({extension_id})\n"
                    f"Call ID: {call.get('id', 'Unknown')}"
                )
                self.add_note_to_lead(lead_id, note_content)
                
            return lead_id
            
    except Exception as e:
        logger.error(f"Error creating/updating lead for call {call.get('id')}: {str(e)}")
        return None
        
def update_lead_status(self, lead_id, status):
    """Update a lead's status in Zoho CRM."""
    self._ensure_valid_token()
    
    url = f"{self.base_url}/Leads/{lead_id}"
    headers = {
        "Authorization": f"Zoho-oauthtoken {self.access_token}",
        "Content-Type": "application/json"
    }
    data = {
        "data": [
            {
                "Lead_Status": status
            }
        ]
    }
    
    try:
        response = requests.put(url, headers=headers, json=data)
        if response.status_code in [200, 201, 202]:
            logger.info(f"Successfully updated lead {lead_id} status to '{status}'")
            return True
        else:
            logger.error(f"Error updating lead status: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Exception updating lead status: {str(e)}")
        return False
```

## 6. Main Processing Function

Update the main processing function with call qualification and proper statistics:

```python
def process_accepted_calls(call_logs, zoho_client, extension_ids, extension_names, lead_owners, rc_client, dry_run=False):
    """Process accepted calls and create leads in Zoho CRM."""
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
    
    # Process each call
    for call in call_logs:
        # Skip calls that don't have required data
        if not call.get('from') or not call.get('to'):
            logger.warning(f"Skipping call {call.get('id')} - missing required data")
            stats['skipped_calls'] += 1
            continue
            
        # Qualify the call (should already be done by get_call_logs, but double-check)
        if not qualify_call(call):
            logger.debug(f"Call {call.get('id')} did not qualify as 'accepted', skipping")
            stats['skipped_calls'] += 1
            continue
            
        stats['qualified_calls'] += 1
        
        # Get the extension ID from the call
        extension_id = call['to'].get('extensionId')
        if not extension_id or str(extension_id) not in extension_ids:
            logger.warning(f"Skipping qualified call {call.get('id')} - extension {extension_id} not in configured extensions")
            stats['skipped_calls'] += 1
            continue

        # Get the caller's phone number
        phone_number = call['from']['phoneNumber']
            
        # Get the next lead owner in the round-robin cycle
        lead_owner = next(lead_owner_cycle)

        # Create or update the lead in Zoho CRM (this will check for existing leads)
        if not dry_run:
            lead_id = zoho_client.create_or_update_lead(call, lead_owner, extension_names)
            if lead_id:
                stats['processed_calls'] += 1
                
                # Check if an existing lead was updated or a new one created
                existing_lead = zoho_client.search_records("Leads", f"id:equals:{lead_id}")
                if existing_lead and existing_lead[0].get('Created_Time'):
                    created_time = existing_lead[0].get('Created_Time')
                    call_time = call.get('startTime', '')
                    
                    # If lead was created before this call, it's an existing lead
                    if created_time < call_time:
                        stats['existing_leads'] += 1
                    else:
                        stats['new_leads'] += 1
                else:
                    stats['new_leads'] += 1
                
                # Handle recording attachment
                if 'recording' in call and call['recording'] and 'id' in call['recording']:
                    try:
                        # Extract call receive time for the filename
                        call_receive_time = call.get('startTime')
                        if call_receive_time:
                            try:
                                call_time = datetime.fromisoformat(call_receive_time.replace('Z', '+00:00'))
                            except ValueError:
                                call_time = datetime.now()
                        else:
                            call_time = datetime.now()
                            
                        recording_success = zoho_client.attach_recording_to_lead(call, lead_id, rc_client, call_time)
                        if recording_success:
                            stats['recordings_attached'] += 1
                        else:
                            stats['recording_failures'] += 1
                    except Exception as e:
                        logger.error(f"Error attaching recording: {str(e)}")
                        stats['recording_failures'] += 1
        else:
            # Dry run mode
            logger.info(f"[DRY-RUN] Would process qualified call {call.get('id')} from {phone_number}")
            stats['processed_calls'] += 1
            
            # Check if it would be a new or existing lead
            existing_lead = zoho_client.search_records("Leads", f"Phone:equals:{phone_number}")
            if existing_lead:
                stats['existing_leads'] += 1
                logger.info(f"[DRY-RUN] Would update existing lead {existing_lead[0]['id']} for {phone_number}")
            else:
                stats['new_leads'] += 1
                logger.info(f"[DRY-RUN] Would create new lead for {phone_number}")

    # Log statistics
    logger.info(f"Call Processing Summary:")
    logger.info(f"  Total calls found: {stats['total_calls']}")
    logger.info(f"  Calls qualified as 'accepted': {stats['qualified_calls']}")
    logger.info(f"  Calls processed: {stats['processed_calls']}")
    logger.info(f"  Existing leads updated: {stats['existing_leads']}")
    logger.info(f"  New leads created: {stats['new_leads'] if not dry_run else '0 (dry run)'}")
    logger.info(f"  Calls skipped: {stats['skipped_calls']}")
    logger.info(f"  Recordings attached: {stats['recordings_attached']}")
    logger.info(f"  Recording failures: {stats['recording_failures']}")

    return stats
```

## 7. Complete Main Function

The main function should include robust error handling and clear statistics:

```python
def main():
    """Main function"""
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
            file_handler = logging.FileHandler(args.log_file)
            file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
            logger.addHandler(file_handler)
            logger.info(f"Logging to custom log file: {args.log_file}")
        
        # Display script mode and options
        mode = "DRY RUN" if args.dry_run else "PRODUCTION"
        logger.info(f"Starting accepted calls processing in {mode} mode")
        
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
        
        # Load configuration files
        try:
            extensions_file = args.extensions_file or os.path.join(data_dir, 'extensions.json')
            extensions = storage.load_json_file(extensions_file)
            if not extensions:
                logger.error(f"No extensions found in {extensions_file}")
                return 1
                
            lead_owners_file = args.lead_owners_file or os.path.join(data_dir, 'lead_owners.json')
            lead_owners = storage.load_json_file(lead_owners_file)
            if not lead_owners:
                logger.error(f"No lead owners found in {lead_owners_file}")
                return 1
                
            logger.info(f"Loaded {len(extensions)} extensions and {len(lead_owners)} lead owners")
        except Exception as e:
            logger.error(f"Error loading configuration files: {str(e)}")
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
        logger.info(f"Starting to process {len(extensions)} extensions")
        for extension in extensions:
            logger.info(f"Processing calls for extension {extension['name']} (ID: {extension['id']})")
            
            try:
                # Get call logs for this extension
                call_logs = rc_client.get_call_logs(extension['id'], start_date, end_date)
                logger.info(f"Retrieved {len(call_logs)} calls for extension {extension['name']}")
                
                # Process the calls
                stats = process_accepted_calls(call_logs, zoho_client, extension_ids, extension_names, lead_owners, rc_client, args.dry_run)
                
                # Aggregate statistics
                if stats:
                    for key in overall_stats:
                        if key in stats:
                            overall_stats[key] += stats.get(key, 0)
            except Exception as e:
                logger.error(f"Error processing extension {extension['name']}: {str(e)}")
                continue
            
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
        logger.info(f"  Recordings attached: {overall_stats['recordings_attached']}")
        logger.info(f"  Recording failures: {overall_stats['recording_failures']}")
        
        logger.info("Processing completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Unhandled error in main: {str(e)}")
        logger.debug(f"Stack trace:", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

These code examples cover the main components that need to be implemented or improved in the `accepted_calls.py` script. The most important part is the `qualify_call` function, which ensures only truly accepted calls are processed, and the proper integration of this function into the call retrieval and processing pipeline. 