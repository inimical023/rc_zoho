# AcceptedCalls.py Requirements

## Overview
The `accepted_calls.py` script is part of a RingCentral-Zoho integration system that processes accepted inbound calls, creates/updates leads in Zoho CRM, and attaches call recordings. This document details the requirements and functionality that must be implemented.

## Core Functionality

### 1. Call Qualification
- **API-Level Filtering**:
  - Filter calls at the API level with parameters: `direction=Inbound`, `type=Voice`
  - Retrieve detailed view of calls with recording information
  - Implement pagination with higher limit (250 per page)

- **Call Leg Analysis**:
  - Add a `qualify_call` function that examines call legs
  - A call is considered "accepted" if at least one leg has `result: "Accepted"`
  - Skip calls marked as spam, blocked, or with unknown result
  - Analyze telephony status to determine if call was truly connected

### 2. Credential Management
- **Token Management**:
  - Use secure credential storage via the `SecureStorage` class from `common.py`
  - Implement token refresh capabilities for both RingCentral and Zoho APIs
  - Handle expired credentials gracefully with useful error messages
  - Add token refresh logic to refresh Zoho access token when needed

### 3. Lead Creation in Zoho
- **Existing Lead Processing**:
  - Search existing leads by phone number
  - If lead exists, add detailed note with call information
  - Update lead status to "Accepted Call"

- **New Lead Creation**:
  - Create leads with owner assignment using round-robin from `lead_owners.json`
  - Set appropriate lead source from the target extension
  - Set lead status to "Accepted Call"
  - Add detailed note about call information
  - Add placeholder first/last name fields for unknown callers

### 4. Recording Management
- **Recording Attachment**:
  - Check if recording is already attached to prevent duplicates
  - Implement rate limiting with exponential backoff for recording requests
  - Format recording filenames with timestamp: `{timestamp}_recording_{id}.{extension}`
  - Handle different recording formats (MP3, WAV)
  - Add note if recording attachment fails

### 5. Error Handling & Logging
- **Robust Error Handling**:
  - Implement try/except blocks around all API calls
  - Log API response codes and error messages
  - Handle rate limiting with exponential backoff
  - Retry logic for transient errors

- **Comprehensive Logging**:
  - Log processing statistics (calls processed, leads created/updated, etc.)
  - Detailed debug logging option for troubleshooting
  - Log clear success/failure messages for each API operation

### 6. Script Command-Line Options
- **Flexible Date Range Processing**:
  - Support processing calls from specific date range
  - Support processing calls from last N hours
  - Default to last 24 hours if no date range specified

- **Control Options**:
  - `--dry-run` mode to simulate changes without modifying Zoho
  - `--debug` flag for verbose logging
  - Support for custom extensions and lead owners file paths

## Technical Requirements

### API Integration Details
1. **RingCentral API**:
   - Use JWT authentication flow
   - Implement token refresh logic
   - Properly handle rate limits with backoff strategies
   - Support call recording content retrieval

2. **Zoho CRM API**:
   - Use OAuth 2.0 with refresh token
   - Implement search, create, update operations for leads
   - Support file attachment for recordings
   - Add detailed notes to leads

### Code Organization
- Maintain object-oriented approach with dedicated client classes
- Clear separation of concerns between API interaction and business logic
- Reuse common code from `common.py`

### Dependencies
- Handle package dependencies with explicit version requirements
- Implement dependency checking and installation
- Support both Windows and Linux environments

## Implementation Requirements

### From Existing Code
Copy and adapt the following sections from the current `accepted_calls.py`:

1. Import statements and dependency checking
2. SecureStorage integration
3. Command-line argument parsing
4. Client classes structure (RingCentralClient and ZohoClient)
5. Main function flow
6. Date range handling
7. Logging configuration

### New Functionality to Add
1. Implement proper call qualification using call legs analysis
2. Add API-level filtering for efficiency
3. Enhance the lead creation process
4. Improve recording attachment process
5. Add robust error handling with retries
6. Implement token refresh for both APIs
7. Add detailed statistics reporting

## Testing Requirements
- Test with various call scenarios (accepted, missed, multiple legs)
- Verify lead creation and updates in Zoho
- Test recording attachment functionality
- Verify command-line options work correctly
- Test error handling with simulated API failures

## Performance Considerations
- Optimize API calls to minimize rate limiting
- Handle large call volumes efficiently
- Implement pagination for retrieving many calls
- Consider batch processing for lead updates when possible

## Security Requirements
- Never log sensitive credentials
- Use secure storage for all tokens and secrets
- Implement proper access token management
- Handle credentials expiration gracefully

---

By implementing these requirements, the `accepted_calls.py` script will properly filter for accepted calls, create or update leads in Zoho CRM, attach recordings when available, and provide robust error handling and reporting. 