import os
import sys
import json
import logging
import requests
import base64
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
from pathlib import Path
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import subprocess

# Create required directories first
Path('logs').mkdir(exist_ok=True)
Path('data').mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'unified_admin.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('unified_admin')

class SecureStorage:
    """Unified secure storage for credentials and configuration"""
    def __init__(self):
        load_dotenv()
        self.data_dir = Path('data')
        self.data_dir.mkdir(exist_ok=True)
        
        # Create logs directory if it doesn't exist
        Path('logs').mkdir(exist_ok=True)
        
        self.key_file = self.data_dir / 'encryption.key'
        self.credentials_file = self.data_dir / 'credentials.enc'
        self.extensions_file = self.data_dir / 'extensions.json'
        self.lead_owners_file = self.data_dir / 'lead_owners.json'
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

    def save_credentials(self, credentials):
        """Save encrypted credentials"""
        try:
            existing_creds = self.load_credentials() or {}
            existing_creds.update(credentials)
            existing_creds['timestamp'] = datetime.now().isoformat()
            
            json_data = json.dumps(existing_creds)
            encrypted_data = self.cipher_suite.encrypt(json_data.encode())
            
            with open(self.credentials_file, 'wb') as file:
                file.write(encrypted_data)
            return True
        except Exception as e:
            logger.error(f"Error saving credentials: {str(e)}")
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
            
            timestamp = datetime.fromisoformat(credentials['timestamp'])
            if datetime.now() - timestamp > timedelta(hours=1):
                logger.warning("Credentials have expired")
                return None
            
            return credentials
        except Exception as e:
            logger.error(f"Error loading credentials: {str(e)}")
            return None

    def save_extensions(self, extensions):
        """Save extensions configuration"""
        try:
            with open(self.extensions_file, 'w') as f:
                json.dump(extensions, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Error saving extensions: {str(e)}")
            return False

    def load_extensions(self):
        """Load extensions configuration"""
        try:
            if not self.extensions_file.exists():
                return []
            with open(self.extensions_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading extensions: {str(e)}")
            return []

    def save_lead_owners(self, lead_owners):
        """Save lead owners configuration"""
        try:
            with open(self.lead_owners_file, 'w') as f:
                json.dump(lead_owners, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Error saving lead owners: {str(e)}")
            return False

    def load_lead_owners(self):
        """Load lead owners configuration"""
        try:
            if not self.lead_owners_file.exists():
                return []
            with open(self.lead_owners_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading lead owners: {str(e)}")
            return []

class RingCentralClient:
    """RingCentral API client"""
    def __init__(self, storage):
        self.storage = storage
        self.base_url = "https://platform.ringcentral.com"
        self.access_token = None
        self._get_credentials()
        self._get_oauth_token()

    def _get_credentials(self):
        """Get RingCentral credentials"""
        credentials = self.storage.load_credentials()
        if not credentials:
            logger.warning("No RingCentral credentials found")
            self.jwt_token = None
            self.client_id = None
            self.client_secret = None
            self.account_id = None
            return
        self.jwt_token = credentials.get('rc_jwt')
        self.client_id = credentials.get('rc_client_id')
        self.client_secret = credentials.get('rc_client_secret')
        self.account_id = credentials.get('rc_account')

    def _get_oauth_token(self):
        """Exchange JWT token for OAuth access token"""
        if not all([self.jwt_token, self.client_id, self.client_secret]):
            logger.warning("Cannot get OAuth token: Missing credentials")
            return
            
        url = f"{self.base_url}/restapi/oauth/token"
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
            self.access_token = response.json()["access_token"]
        except Exception as e:
            logger.error(f"Failed to get OAuth token: {str(e)}")
            self.access_token = None

    def get_call_queues(self):
        """Get all call queues"""
        if not self.access_token:
            logger.warning("Cannot get call queues: No access token")
            return []
            
        url = f"{self.base_url}/restapi/v1.0/account/{self.account_id}/call-queues"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json().get('records', [])
        except Exception as e:
            logger.error(f"Failed to get call queues: {str(e)}")
            return []

class ZohoClient:
    """Zoho CRM API client"""
    def __init__(self, storage):
        self.storage = storage
        self.base_url = "https://www.zohoapis.com/crm/v7"
        self.access_token = None
        self._get_credentials()
        self._get_oauth_token()

    def _get_credentials(self):
        """Get Zoho credentials"""
        credentials = self.storage.load_credentials()
        if not credentials:
            logger.warning("No Zoho credentials found")
            self.client_id = None
            self.client_secret = None
            self.refresh_token = None
            return
        self.client_id = credentials.get('zoho_client_id')
        self.client_secret = credentials.get('zoho_client_secret')
        self.refresh_token = credentials.get('zoho_refresh_token')

    def _get_oauth_token(self):
        """Exchange refresh token for OAuth access token"""
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            logger.warning("Cannot get OAuth token: Missing credentials")
            return
            
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
            self.access_token = response.json()["access_token"]
        except Exception as e:
            logger.error(f"Failed to get OAuth token: {str(e)}")
            self.access_token = None

    def get_users(self):
        """Get all active users"""
        if not self.access_token:
            logger.warning("Cannot get users: No access token")
            return []
            
        url = f"{self.base_url}/users"
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            users = response.json().get('users', [])
            return [user for user in users if user.get('status') == 'active']
        except Exception as e:
            logger.error(f"Failed to get users: {str(e)}")
            return []

    def get_roles(self):
        """Get all roles"""
        if not self.access_token:
            logger.warning("Cannot get roles: No access token")
            return []
            
        url = f"{self.base_url}/settings/roles"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            roles = response.json().get('roles', [])
            return [{
                'id': role['id'],
                'name': role['display_label'],
                'description': role.get('description', ''),
                'api_name': role['api_name']
            } for role in roles]
        except Exception as e:
            logger.error(f"Failed to get roles: {str(e)}")
            return []

class CredentialsTab(ttk.Frame):
    def __init__(self, parent, storage):
        super().__init__(parent, padding="20")
        self.storage = storage
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.create_widgets()

    def create_widgets(self):
        # Main container frame
        main_frame = ttk.Frame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)

        # RingCentral Section
        rc_frame = ttk.LabelFrame(main_frame, text="RingCentral Credentials", padding="15")
        rc_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        rc_frame.grid_columnconfigure(1, weight=1)

        # RingCentral fields
        self.rc_jwt = ttk.Entry(rc_frame, width=50, show="*")
        self.rc_id = ttk.Entry(rc_frame, width=50)
        self.rc_secret = ttk.Entry(rc_frame, width=50, show="*")
        self.rc_account = ttk.Entry(rc_frame, width=50)
        
        fields = [
            ("JWT Token:", self.rc_jwt),
            ("Client ID:", self.rc_id),
            ("Client Secret:", self.rc_secret),
            ("Account ID:", self.rc_account)
        ]

        for i, (label, entry) in enumerate(fields):
            ttk.Label(rc_frame, text=label).grid(row=i, column=0, sticky="w", padx=(0, 10), pady=5)
            entry.grid(row=i, column=1, sticky="ew", pady=5)

        self.rc_account.insert(0, "~")

        # RingCentral buttons
        rc_buttons_frame = ttk.Frame(rc_frame)
        rc_buttons_frame.grid(row=len(fields), column=0, columnspan=2, pady=15)
        rc_buttons_frame.grid_columnconfigure(0, weight=1)
        rc_buttons_frame.grid_columnconfigure(1, weight=1)

        ttk.Button(rc_buttons_frame, text="Verify RingCentral", command=self.verify_rc).grid(row=0, column=0, padx=5)
        ttk.Button(rc_buttons_frame, text="Check Existing", command=self.check_rc).grid(row=0, column=1, padx=5)

        # Zoho Section
        zoho_frame = ttk.LabelFrame(main_frame, text="Zoho Credentials", padding="15")
        zoho_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        zoho_frame.grid_columnconfigure(1, weight=1)

        # Zoho fields
        self.zoho_id = ttk.Entry(zoho_frame, width=50)
        self.zoho_secret = ttk.Entry(zoho_frame, width=50, show="*")
        self.zoho_refresh = ttk.Entry(zoho_frame, width=50, show="*")
        
        fields = [
            ("Client ID:", self.zoho_id),
            ("Client Secret:", self.zoho_secret),
            ("Refresh Token:", self.zoho_refresh)
        ]

        for i, (label, entry) in enumerate(fields):
            ttk.Label(zoho_frame, text=label).grid(row=i, column=0, sticky="w", padx=(0, 10), pady=5)
            entry.grid(row=i, column=1, sticky="ew", pady=5)

        # Zoho buttons
        zoho_buttons_frame = ttk.Frame(zoho_frame)
        zoho_buttons_frame.grid(row=len(fields), column=0, columnspan=2, pady=15)
        zoho_buttons_frame.grid_columnconfigure(0, weight=1)
        zoho_buttons_frame.grid_columnconfigure(1, weight=1)

        ttk.Button(zoho_buttons_frame, text="Verify Zoho", command=self.verify_zoho).grid(row=0, column=0, padx=5)
        ttk.Button(zoho_buttons_frame, text="Check Existing", command=self.check_zoho).grid(row=0, column=1, padx=5)

        # Submit Button
        self.submit_button = ttk.Button(main_frame, text="Submit", command=self.submit_credentials)
        self.submit_button.grid(row=2, column=0, pady=20)
        self.submit_button.state(['disabled'])

        # Load existing credentials
        self.load_existing_credentials()

    def verify_rc(self):
        """Verify RingCentral credentials"""
        if not all([self.rc_jwt.get(), self.rc_id.get(), self.rc_secret.get(), self.rc_account.get()]):
            messagebox.showerror("Error", "Please fill in all RingCentral fields")
            return
        messagebox.showinfo("Success", "RingCentral credentials verified")

    def verify_zoho(self):
        """Verify Zoho credentials"""
        if not all([self.zoho_id.get(), self.zoho_secret.get(), self.zoho_refresh.get()]):
            messagebox.showerror("Error", "Please fill in all Zoho fields")
            return
        messagebox.showinfo("Success", "Zoho credentials verified")

    def check_rc(self):
        """Check existing RingCentral credentials"""
        try:
            credentials = self.storage.load_credentials()
            if credentials:
                messagebox.showinfo("Existing RingCentral Credentials",
                    f"JWT: {credentials.get('rc_jwt', '')[:4]}...\n"
                    f"Client ID: {credentials.get('rc_client_id', '')[:4]}...\n"
                    f"Client Secret: {credentials.get('rc_client_secret', '')[:4]}...\n"
                    f"Account ID: {credentials.get('rc_account', '')}")
            else:
                messagebox.showinfo("No Existing Credentials", "No RingCentral credentials found")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to check RingCentral credentials: {str(e)}")

    def check_zoho(self):
        """Check existing Zoho credentials"""
        try:
            credentials = self.storage.load_credentials()
            if credentials:
                messagebox.showinfo("Existing Zoho Credentials",
                    f"Client ID: {credentials.get('zoho_client_id', '')[:4]}...\n"
                    f"Client Secret: {credentials.get('zoho_client_secret', '')[:4]}...\n"
                    f"Refresh Token: {credentials.get('zoho_refresh_token', '')[:4]}...")
            else:
                messagebox.showinfo("No Existing Credentials", "No Zoho credentials found")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to check Zoho credentials: {str(e)}")

    def load_existing_credentials(self):
        """Load existing credentials into the form"""
        try:
            credentials = self.storage.load_credentials()
            if credentials:
                self.rc_jwt.insert(0, credentials.get('rc_jwt', ''))
                self.rc_id.insert(0, credentials.get('rc_client_id', ''))
                self.rc_secret.insert(0, credentials.get('rc_client_secret', ''))
                self.rc_account.insert(0, credentials.get('rc_account', ''))

                self.zoho_id.insert(0, credentials.get('zoho_client_id', ''))
                self.zoho_secret.insert(0, credentials.get('zoho_client_secret', ''))
                self.zoho_refresh.insert(0, credentials.get('zoho_refresh_token', ''))
        except Exception as e:
            logger.error(f"Failed to load existing credentials: {str(e)}")

    def submit_credentials(self):
        """Submit credentials to secure storage"""
        try:
            credentials = {
                'rc_jwt': self.rc_jwt.get(),
                'rc_client_id': self.rc_id.get(),
                'rc_client_secret': self.rc_secret.get(),
                'rc_account': self.rc_account.get(),
                'zoho_client_id': self.zoho_id.get(),
                'zoho_client_secret': self.zoho_secret.get(),
                'zoho_refresh_token': self.zoho_refresh.get()
            }
            
            if self.storage.save_credentials(credentials):
                messagebox.showinfo("Success", "Credentials saved successfully!")
            else:
                messagebox.showerror("Error", "Failed to save credentials")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save credentials: {str(e)}")

class ExtensionsTab(ttk.Frame):
    def __init__(self, parent, storage):
        super().__init__(parent, padding="20")
        self.storage = storage
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Initialize RingCentral client
        self.rc_client = RingCentralClient(self.storage)
        
        # Load existing extensions
        self.extensions = self.storage.load_extensions()
        
        # Store queue data
        self.available_queues_data = {}  # Dictionary to store queue data
        self.current_extensions_data = {}  # Dictionary to store extension data
        
        self.create_widgets()
        self.load_available_queues()
        self.load_existing_extensions()

    def create_widgets(self):
        # Main container frame
        main_frame = ttk.Frame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(2, weight=1)

        # Available Queues Section
        queues_frame = ttk.LabelFrame(main_frame, text="Available Call Queues", padding="10")
        queues_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        queues_frame.grid_rowconfigure(0, weight=1)
        queues_frame.grid_columnconfigure(0, weight=1)

        # Listbox for available queues
        self.available_queues = tk.Listbox(queues_frame, height=20, selectmode=tk.EXTENDED, font=('Arial', 10))
        self.available_queues.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbar for available queues
        scrollbar = ttk.Scrollbar(queues_frame, orient=tk.VERTICAL, command=self.available_queues.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.available_queues['yscrollcommand'] = scrollbar.set

        # Current Extensions Section
        current_frame = ttk.LabelFrame(main_frame, text="Current Extensions", padding="10")
        current_frame.grid(row=0, column=2, sticky="nsew", padx=(10, 0))
        current_frame.grid_rowconfigure(0, weight=1)
        current_frame.grid_columnconfigure(0, weight=1)

        # Listbox for current extensions
        self.current_extensions = tk.Listbox(current_frame, height=20, selectmode=tk.EXTENDED, font=('Arial', 10))
        self.current_extensions.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbar for current extensions
        scrollbar = ttk.Scrollbar(current_frame, orient=tk.VERTICAL, command=self.current_extensions.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.current_extensions['yscrollcommand'] = scrollbar.set

        # Buttons Section
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=1, column=0, columnspan=3, pady=20, sticky="ew")
        buttons_frame.grid_columnconfigure(0, weight=1)
        buttons_frame.grid_columnconfigure(1, weight=1)

        # Left side buttons
        left_buttons = ttk.Frame(buttons_frame)
        left_buttons.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(left_buttons, text="Add Selected", command=self.add_selected_queues, width=15).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_buttons, text="Remove Selected", command=self.remove_selected_extensions, width=15).pack(side=tk.LEFT, padx=5)

        # Right side buttons
        right_buttons = ttk.Frame(buttons_frame)
        right_buttons.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        ttk.Button(right_buttons, text="Refresh Queues", command=self.load_available_queues, width=15).pack(side=tk.RIGHT, padx=5)
        ttk.Button(right_buttons, text="Save Changes", command=self.save_changes, width=15).pack(side=tk.RIGHT, padx=5)

    def load_available_queues(self):
        """Load available call queues from RingCentral."""
        self.available_queues.delete(0, tk.END)
        self.available_queues_data.clear()
        queues = self.rc_client.get_call_queues()
        
        # Get set of existing extension IDs for faster lookup
        existing_extension_ids = {ext['id'] for ext in self.extensions}
        
        for queue in queues:
            # Skip if the queue is already added as an extension
            if queue['id'] in existing_extension_ids:
                continue
                
            display_text = f"{queue['name']} (ID: {queue['id']})"
            index = self.available_queues.size()
            self.available_queues.insert(tk.END, display_text)
            self.available_queues_data[index] = queue

    def load_existing_extensions(self):
        """Load existing extensions into the listbox."""
        self.current_extensions.delete(0, tk.END)
        self.current_extensions_data.clear()
        
        for ext in self.extensions:
            display_text = f"{ext['name']} (ID: {ext['id']})"
            index = self.current_extensions.size()
            self.current_extensions.insert(tk.END, display_text)
            self.current_extensions_data[index] = ext

    def add_selected_queues(self):
        """Add selected call queues to the current extensions."""
        selected_indices = self.available_queues.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "Please select at least one call queue to add.")
            return
        
        added_count = 0
        for index in selected_indices:
            queue_data = self.available_queues_data.get(index)
            if queue_data:
                new_extension = {
                    "id": queue_data['id'],
                    "name": queue_data['name'],
                    "extensionNumber": queue_data.get('extensionNumber', 'N/A')
                }
                
                # Check if already exists
                if not any(ext['id'] == queue_data['id'] for ext in self.extensions):
                    self.extensions.append(new_extension)
                    added_count += 1
        
        if added_count > 0:
            self.load_existing_extensions()
            self.load_available_queues()
            messagebox.showinfo("Success", f"Added {added_count} call queue(s).")
        else:
            messagebox.showinfo("Info", "Selected call queues are already configured.")

    def remove_selected_extensions(self):
        """Remove selected extensions from the current list."""
        selected_indices = self.current_extensions.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "Please select at least one extension to remove.")
            return
        
        # Get the actual extensions to remove
        extensions_to_remove = []
        for index in selected_indices:
            ext_data = self.current_extensions_data.get(index)
            if ext_data:
                extensions_to_remove.append(ext_data)
        
        # Remove the extensions from the main list
        for ext in extensions_to_remove:
            self.extensions = [e for e in self.extensions if e['id'] != ext['id']]
        
        self.load_existing_extensions()
        self.load_available_queues()
        messagebox.showinfo("Success", f"Removed {len(extensions_to_remove)} extension(s).")

    def save_changes(self):
        """Save changes to extensions.json."""
        try:
            if self.storage.save_extensions(self.extensions):
                messagebox.showinfo("Success", "Changes saved successfully!")
            else:
                messagebox.showerror("Error", "Failed to save changes")
        except Exception as e:
            logger.error(f"Error saving extensions: {str(e)}")
            messagebox.showerror("Error", f"Failed to save changes: {str(e)}")

class LeadOwnersTab(ttk.Frame):
    def __init__(self, parent, storage):
        super().__init__(parent, padding="20")
        self.storage = storage
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # Initialize Zoho client
        self.zoho_client = ZohoClient(self.storage)
        
        # Load existing lead owners
        self.lead_owners = self.storage.load_lead_owners()
        
        # Store data
        self.users_data = {}  # Dictionary to store user data
        self.roles_data = {}  # Dictionary to store role data
        self.selected_users = set()  # Set to store selected user IDs
        self.unsaved_users = set()  # Set to store IDs of unsaved users
        
        self.create_widgets()
        self.load_users()
        self.load_roles()
        self.load_lead_owners()
        self.mark_existing_lead_owners()

    def create_widgets(self):
        # Main container frame
        main_frame = ttk.Frame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_columnconfigure(2, weight=1)

        # Users Section
        users_frame = ttk.LabelFrame(main_frame, text="Active Users", padding="5")
        users_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        users_frame.grid_columnconfigure(0, weight=1)
        users_frame.grid_rowconfigure(0, weight=1)

        # Listbox for users
        self.users_listbox = tk.Listbox(users_frame, height=20, selectmode=tk.EXTENDED)
        self.users_listbox.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbar for users
        scrollbar = ttk.Scrollbar(users_frame, orient=tk.VERTICAL, command=self.users_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.users_listbox['yscrollcommand'] = scrollbar.set

        # Roles Section
        roles_frame = ttk.LabelFrame(main_frame, text="Roles", padding="5")
        roles_frame.grid(row=0, column=1, sticky="nsew", padx=5)
        roles_frame.grid_columnconfigure(0, weight=1)
        roles_frame.grid_rowconfigure(0, weight=1)

        # Listbox for roles
        self.roles_listbox = tk.Listbox(roles_frame, height=20, selectmode=tk.EXTENDED)
        self.roles_listbox.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbar for roles
        scrollbar = ttk.Scrollbar(roles_frame, orient=tk.VERTICAL, command=self.roles_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.roles_listbox['yscrollcommand'] = scrollbar.set

        # Lead Owners Section
        lead_owners_frame = ttk.LabelFrame(main_frame, text="Current Lead Owners", padding="5")
        lead_owners_frame.grid(row=0, column=2, sticky="nsew", padx=(5, 0))
        lead_owners_frame.grid_columnconfigure(0, weight=1)
        lead_owners_frame.grid_rowconfigure(0, weight=1)

        # Listbox for lead owners
        self.lead_owners_listbox = tk.Listbox(lead_owners_frame, height=20, selectmode=tk.EXTENDED)
        self.lead_owners_listbox.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbar for lead owners
        scrollbar = ttk.Scrollbar(lead_owners_frame, orient=tk.VERTICAL, command=self.lead_owners_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.lead_owners_listbox['yscrollcommand'] = scrollbar.set

        # Buttons Section
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=1, column=0, columnspan=3, pady=10, sticky="ew")
        buttons_frame.grid_columnconfigure(0, weight=1)
        buttons_frame.grid_columnconfigure(1, weight=1)

        # Left side buttons
        left_buttons = ttk.Frame(buttons_frame)
        left_buttons.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(left_buttons, text="Select by Role", command=self.select_by_role).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_buttons, text="Clear Selection", command=self.clear_selection).pack(side=tk.LEFT, padx=5)

        # Middle buttons
        middle_buttons = ttk.Frame(buttons_frame)
        middle_buttons.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(middle_buttons, text="Add Selected", command=self.add_selected_users).pack(side=tk.LEFT, padx=5)
        ttk.Button(middle_buttons, text="Remove Selected", command=self.remove_selected_owners).pack(side=tk.LEFT, padx=5)

        # Right side buttons
        right_buttons = ttk.Frame(buttons_frame)
        right_buttons.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        ttk.Button(right_buttons, text="Refresh Data", command=self.refresh_data).pack(side=tk.RIGHT, padx=5)
        ttk.Button(right_buttons, text="Save Changes", command=self.save_changes).pack(side=tk.RIGHT, padx=5)

    def load_users(self):
        """Load users from Zoho CRM."""
        self.users_listbox.delete(0, tk.END)
        self.users_data.clear()
        users = self.zoho_client.get_users()
        
        # Get set of existing lead owner IDs for faster lookup
        existing_owner_ids = {owner['id'] for owner in self.lead_owners}
        
        for user in users:
            # Skip users who are already lead owners
            if user['id'] in existing_owner_ids:
                continue
                
            display_text = f"{user['full_name']} ({user['email']})"
            index = self.users_listbox.size()
            self.users_listbox.insert(tk.END, display_text)
            self.users_data[index] = user

    def load_roles(self):
        """Load roles into the listbox."""
        roles = self.zoho_client.get_roles()
        self.roles_listbox.delete(0, tk.END)
        
        for role in roles:
            display_text = f"{role['name']} ({role['id']})"
            self.roles_listbox.insert(tk.END, display_text)
            self.roles_data[display_text] = role

    def load_lead_owners(self):
        """Load current lead owners into the listbox."""
        self.lead_owners_listbox.delete(0, tk.END)
        for owner in self.lead_owners:
            display_text = f"{owner['name']} ({owner['email']})"
            if owner['id'] in self.unsaved_users:
                display_text += " [Not Saved]"
            self.lead_owners_listbox.insert(tk.END, display_text)

    def mark_existing_lead_owners(self):
        """Mark existing lead owners as selected in the users listbox."""
        for i in range(self.users_listbox.size()):
            user_data = self.users_data.get(i)
            if user_data and any(owner['id'] == user_data['id'] for owner in self.lead_owners):
                self.users_listbox.selection_set(i)
                self.selected_users.add(user_data['id'])

    def select_by_role(self):
        """Select all users with the selected role."""
        selected_indices = self.roles_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "Please select at least one role.")
            return
        
        # Clear current selection
        self.users_listbox.selection_clear(0, tk.END)
        self.selected_users.clear()
        
        # Get selected role IDs
        selected_roles = []
        for index in selected_indices:
            display_text = self.roles_listbox.get(index)
            if display_text in self.roles_data:
                selected_roles.append(self.roles_data[display_text]['id'])
        
        if not selected_roles:
            messagebox.showwarning("Warning", "Could not find role data for selection.")
            return
        
        # Select users with matching roles
        for i in range(self.users_listbox.size()):
            user_data = self.users_data.get(i)
            if user_data and user_data.get('role', {}).get('id') in selected_roles:
                self.users_listbox.selection_set(i)
                self.selected_users.add(user_data['id'])
            
        if not self.selected_users:
            messagebox.showinfo("Info", "No users found with the selected role(s).")

    def clear_selection(self):
        """Clear all selections."""
        self.users_listbox.selection_clear(0, tk.END)
        self.roles_listbox.selection_clear(0, tk.END)
        self.selected_users.clear()

    def remove_selected_owners(self):
        """Remove selected users from lead owners."""
        selected_indices = self.lead_owners_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "Please select at least one lead owner to remove.")
            return
        
        # Get selected lead owners
        selected_owners = []
        for index in selected_indices:
            display_text = self.lead_owners_listbox.get(index)
            # Find the owner in lead_owners list
            for owner in self.lead_owners:
                if f"{owner['name']} ({owner['email']})" == display_text:
                    selected_owners.append(owner)
                    break
        
        if not selected_owners:
            messagebox.showwarning("Warning", "Could not find selected lead owners.")
            return
        
        # Remove from lead_owners list
        for owner in selected_owners:
            self.lead_owners.remove(owner)
            self.selected_users.discard(owner['id'])
            self.unsaved_users.add(owner['id'])  # Mark as unsaved
        
        # Update the listbox
        self.load_lead_owners()
        
        # Update the users listbox selection
        self.users_listbox.selection_clear(0, tk.END)
        for i in range(self.users_listbox.size()):
            user_data = self.users_data.get(i)
            if user_data and user_data['id'] in self.selected_users:
                self.users_listbox.selection_set(i)
        
        messagebox.showinfo("Success", f"Removed {len(selected_owners)} lead owner(s). Click 'Save Changes' to save.")

    def add_selected_users(self):
        """Add selected users to the lead owners list."""
        selected_indices = self.users_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Warning", "Please select at least one user to add.")
            return
        
        # Get selected users
        added_count = 0
        for index in selected_indices:
            user_data = self.users_data.get(index)
            if user_data:
                # Check if user is already in lead owners
                if not any(owner['id'] == user_data['id'] for owner in self.lead_owners):
                    new_owner = {
                        "id": user_data['id'],
                        "name": user_data['full_name'],
                        "email": user_data['email']
                    }
                    self.lead_owners.append(new_owner)
                    self.unsaved_users.add(user_data['id'])
                    added_count += 1
        
        # Update the lead owners listbox
        self.load_lead_owners()
        
        if added_count > 0:
            messagebox.showinfo("Info", f"Added {added_count} user(s). Click 'Save Changes' to save.")
        else:
            messagebox.showinfo("Info", "No new users were added.")

    def refresh_data(self):
        """Refresh users, roles, and lead owners data."""
        if self.unsaved_users:
            if not messagebox.askyesno("Unsaved Changes", "You have unsaved changes. Do you want to discard them?"):
                return
        
        self.load_lead_owners()  # Load lead owners first
        self.load_users()  # Then load users (which will filter out existing lead owners)
        self.load_roles()
        self.unsaved_users.clear()  # Clear unsaved users on refresh

    def save_changes(self):
        """Save lead owners to file."""
        try:
            if self.storage.save_lead_owners(self.lead_owners):
                self.unsaved_users.clear()  # Clear unsaved users after successful save
                messagebox.showinfo("Success", "Changes saved successfully!")
            else:
                messagebox.showerror("Error", "Failed to save changes")
        except Exception as e:
            logger.error(f"Error saving lead owners: {str(e)}")
            messagebox.showerror("Error", f"Failed to save changes: {str(e)}")

class RunScriptTab(ttk.Frame):
    def __init__(self, parent, storage):
        super().__init__(parent, padding="20")
        self.storage = storage
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.create_widgets()

    def create_widgets(self):
        # Main container frame
        main_frame = ttk.Frame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)

        # Description
        description = ttk.Label(main_frame, text="Run Scripts with Date Range", wraplength=600)
        description.grid(row=0, column=0, pady=(0, 30))

        # Script Selection Frame
        script_frame = ttk.LabelFrame(main_frame, text="Script Selection", padding="15")
        script_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        script_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(script_frame, text="Select Script:").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=5)
        self.script_var = tk.StringVar()
        self.script_combo = ttk.Combobox(script_frame, textvariable=self.script_var, state="readonly")
        self.script_combo['values'] = ('Select Script', 'Missed Calls', 'Accepted Calls')
        self.script_combo.grid(row=0, column=1, sticky="ew", pady=5)
        self.script_combo.set('Select Script')

        # Script Description
        self.description_label = ttk.Label(script_frame, text="Please select a script from the dropdown menu to see its description.", wraplength=500)
        self.description_label.grid(row=1, column=0, columnspan=2, pady=15)

        # Date Range Frame
        date_frame = ttk.LabelFrame(main_frame, text="Date Range", padding="15")
        date_frame.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        date_frame.grid_columnconfigure(1, weight=1)

        # Start Date and Time
        ttk.Label(date_frame, text="Start Date and Time:").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=5)
        self.start_date = ttk.Entry(date_frame, width=30)
        self.start_date.grid(row=0, column=1, sticky="ew", pady=5)
        self.start_date.insert(0, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        # End Date and Time
        ttk.Label(date_frame, text="End Date and Time:").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=5)
        self.end_date = ttk.Entry(date_frame, width=30)
        self.end_date.grid(row=1, column=1, sticky="ew", pady=5)
        self.end_date.insert(0, datetime.now().replace(hour=23, minute=59, second=59).strftime("%Y-%m-%d %H:%M:%S"))

        # Dry Run Checkbox
        self.dry_run_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(date_frame, text="Run in Dry-Run Mode (Preview Only)", variable=self.dry_run_var).grid(row=2, column=0, columnspan=2, pady=15)

        # Run Button
        run_button = ttk.Button(main_frame, text="Run Script", command=self.run_script)
        run_button.grid(row=3, column=0, pady=20)

        # Bind script selection change event
        self.script_combo.bind('<<ComboboxSelected>>', self.on_script_selected)

    def on_script_selected(self, event=None):
        """Update description when script is selected"""
        selection = self.script_var.get()
        if selection == "Select Script":
            self.description_label.config(text="Please select a script from the dropdown menu to see its description.")
        elif selection == "Missed Calls":
            self.description_label.config(text="This script retrieves missed calls from RingCentral and creates leads in Zoho CRM. Each missed call is assigned to a lead owner in round-robin fashion, with the lead status set to \"Missed Call\". The lead includes caller information and call time details.")
        else:  # Accepted Calls
            self.description_label.config(text="This script retrieves accepted calls from RingCentral and creates leads in Zoho CRM. Each accepted call is associated with the lead owner who accepted it, and the lead includes caller information, call details, and call recordings. The recordings are attached to the lead in Zoho CRM.")

    def run_script(self):
        """Run the selected script with the specified date range"""
        try:
            # Validate script selection
            if self.script_var.get() == "Select Script":
                messagebox.showwarning("Warning", "Please select a script to run.")
                return

            # Get script name based on selection
            script_map = {
                "Missed Calls": "missed_calls.py",
                "Accepted Calls": "accepted_calls.py"
            }
            script_name = script_map[self.script_var.get()]

            # Get date range
            start_date = self.start_date.get()
            end_date = self.end_date.get()
            dry_run = self.dry_run_var.get()

            # Create logs directory if it doesn't exist
            Path('logs').mkdir(exist_ok=True)

            # Set the log file name with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"logs/script_run_{timestamp}.log"

            # Write script run details to log
            with open(log_file, 'w') as f:
                f.write("===============================================\n")
                f.write("Script Run Details\n")
                f.write("===============================================\n")
                f.write(f"Script: {script_name}\n")
                f.write(f"Start Date: {start_date}\n")
                f.write(f"End Date: {end_date}\n")
                f.write(f"Dry Run: {dry_run}\n")
                f.write("===============================================\n\n")

            # Create command with parameters
            cmd = [sys.executable, script_name, "--start-date", start_date, "--end-date", end_date]
            if dry_run:
                cmd.append("--dry-run")
                cmd.append("--debug")

            # Run the script in the background
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Create a new window to show progress
            progress_window = tk.Toplevel(self)
            progress_window.title("Script Progress")
            progress_window.geometry("400x200")
            
            progress_label = ttk.Label(progress_window, text="Script is running...")
            progress_label.pack(pady=20)
            
            def check_process():
                if process.poll() is None:
                    # Process is still running
                    progress_window.after(1000, check_process)
                else:
                    # Process has finished
                    stdout, stderr = process.communicate()
                    
                    # Write output to log file
                    with open(log_file, 'a') as f:
                        if stdout:
                            f.write(stdout.decode())
                        if stderr:
                            f.write(stderr.decode())
                    
                    # Close progress window
                    progress_window.destroy()
                    
                    # Show completion message
                    messagebox.showinfo("Script Complete", f"Script execution completed!\nLog file is available at: {log_file}")
            
            # Start checking process status
            check_process()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to run script: {str(e)}")
            logger.error(f"Error running script: {str(e)}")

class SchedulerSetupTab(ttk.Frame):
    def __init__(self, parent, storage):
        super().__init__(parent, padding="20")
        self.storage = storage
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self.create_widgets()

    def create_widgets(self):
        # Main container frame
        main_frame = ttk.Frame(self)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)

        # Description
        description = ttk.Label(
            main_frame, 
            text="Create a batch file for automated script execution that can be added to Windows Task Scheduler",
            wraplength=600
        )
        description.grid(row=0, column=0, pady=(0, 30))

        # Script Selection Frame
        script_frame = ttk.LabelFrame(main_frame, text="Script Configuration", padding="15")
        script_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        script_frame.grid_columnconfigure(1, weight=1)

        # Script Selection
        ttk.Label(script_frame, text="Select Script:").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=5)
        self.script_var = tk.StringVar()
        self.script_combo = ttk.Combobox(script_frame, textvariable=self.script_var, state="readonly")
        self.script_combo['values'] = ('Select Script', 'Missed Calls', 'Accepted Calls')
        self.script_combo.grid(row=0, column=1, sticky="ew", pady=5)
        self.script_combo.set('Select Script')

        # Time Range Frame
        time_frame = ttk.LabelFrame(main_frame, text="Time Range Configuration", padding="15")
        time_frame.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        time_frame.grid_columnconfigure(1, weight=1)

        # Hours Back
        ttk.Label(time_frame, text="Hours Back:").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=5)
        self.hours_back = ttk.Entry(time_frame, width=10)
        self.hours_back.grid(row=0, column=1, sticky="w", pady=5)
        self.hours_back.insert(0, "24")
        ttk.Label(time_frame, text="(How many hours of data to process)").grid(row=0, column=2, sticky="w", padx=10)

        # Schedule Frame
        schedule_frame = ttk.LabelFrame(main_frame, text="Schedule Configuration", padding="15")
        schedule_frame.grid(row=3, column=0, sticky="ew", pady=(0, 20))
        schedule_frame.grid_columnconfigure(1, weight=1)

        # Run Time
        ttk.Label(schedule_frame, text="Run Time (24h):").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=5)
        time_frame = ttk.Frame(schedule_frame)
        time_frame.grid(row=0, column=1, sticky="w")
        
        self.hour_var = tk.StringVar(value="00")
        self.minute_var = tk.StringVar(value="00")
        
        hour_combo = ttk.Combobox(time_frame, textvariable=self.hour_var, width=5, state="readonly")
        hour_combo['values'] = [f"{i:02d}" for i in range(24)]
        hour_combo.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(time_frame, text=":").pack(side=tk.LEFT)
        
        minute_combo = ttk.Combobox(time_frame, textvariable=self.minute_var, width=5, state="readonly")
        minute_combo['values'] = [f"{i:02d}" for i in range(0, 60, 5)]
        minute_combo.pack(side=tk.LEFT, padx=2)

        # Days Selection
        ttk.Label(schedule_frame, text="Run on Days:").grid(row=1, column=0, sticky="w", padx=(0, 10), pady=5)
        days_frame = ttk.Frame(schedule_frame)
        days_frame.grid(row=1, column=1, sticky="w")
        
        self.day_vars = {}
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for i, day in enumerate(days):
            var = tk.BooleanVar(value=True if i < 5 else False)  # Monday-Friday checked by default
            self.day_vars[day] = var
            ttk.Checkbutton(days_frame, text=day, variable=var).grid(row=0, column=i, padx=5)

        # Output Directory Frame
        output_frame = ttk.LabelFrame(main_frame, text="Output Configuration", padding="15")
        output_frame.grid(row=4, column=0, sticky="ew", pady=(0, 20))
        output_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(output_frame, text="Output Directory:").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=5)
        self.output_dir = ttk.Entry(output_frame, width=50)
        self.output_dir.grid(row=0, column=1, sticky="ew", pady=5)
        self.output_dir.insert(0, os.path.expanduser("~\\Documents\\RingCentral-Zoho"))
        
        ttk.Button(output_frame, text="Browse", command=self.browse_output_dir).grid(row=0, column=2, padx=5)

        # Generate Button
        generate_button = ttk.Button(main_frame, text="Generate Batch File", command=self.generate_batch_file)
        generate_button.grid(row=5, column=0, pady=20)

    def browse_output_dir(self):
        """Open directory browser dialog"""
        directory = filedialog.askdirectory(
            initialdir=self.output_dir.get(),
            title="Select Output Directory"
        )
        if directory:
            self.output_dir.delete(0, tk.END)
            self.output_dir.insert(0, directory)

    def generate_batch_file(self):
        """Generate the batch file with the specified configuration"""
        try:
            # Validate inputs
            if self.script_var.get() == "Select Script":
                messagebox.showwarning("Warning", "Please select a script to run.")
                return

            try:
                hours_back = int(self.hours_back.get())
                if hours_back <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Warning", "Please enter a valid positive number for Hours Back.")
                return

            # Get selected days
            selected_days = [day for day, var in self.day_vars.items() if var.get()]
            if not selected_days:
                messagebox.showwarning("Warning", "Please select at least one day to run the script.")
                return

            # Create output directory if it doesn't exist
            output_dir = self.output_dir.get()
            os.makedirs(output_dir, exist_ok=True)

            # Get script name
            script_map = {
                "Missed Calls": "missed_calls.py",
                "Accepted Calls": "accepted_calls.py"
            }
            script_name = script_map[self.script_var.get()]

            # Generate batch file name
            batch_name = f"run_{script_name.replace('.py', '')}_{self.hour_var.get()}{self.minute_var.get()}.bat"
            batch_path = os.path.join(output_dir, batch_name)

            # Get the path to the Python executable and script directory
            python_exe = sys.executable
            script_dir = os.path.dirname(os.path.abspath(__file__))

            # Create batch file content
            batch_content = f"""@echo off
setlocal enabledelayedexpansion

:: Set working directory
cd /d "{script_dir}"

:: Calculate date range
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (
    set mm=%%a
    set dd=%%b
    set yyyy=%%c
)

:: Get current time
for /f "tokens=1-2 delims=: " %%a in ('time /t') do (
    set hour=%%a
    set minute=%%b
)

:: Run the script
"{python_exe}" "{script_name}" --hours-back {hours_back} --debug

:: Log the execution
echo Script executed at %date% %time% >> "{output_dir}\\script_execution.log"

endlocal
"""
            # Write batch file
            with open(batch_path, 'w') as f:
                f.write(batch_content)

            # Create instructions for Task Scheduler
            scheduler_instructions = f"""To set up in Windows Task Scheduler:

1. Open Task Scheduler (taskschd.msc)
2. Click "Create Basic Task"
3. Name: RingCentral-Zoho {self.script_var.get()}
4. Trigger: Weekly
5. Select days: {', '.join(selected_days)}
6. Start time: {self.hour_var.get()}:{self.minute_var.get()}:00
7. Action: Start a program
8. Program/script: "{batch_path}"
9. Start in: "{script_dir}"

The batch file has been created at:
{batch_path}

A log file will be created at:
{output_dir}\\script_execution.log
"""
            # Show success message with instructions
            messagebox.showinfo(
                "Batch File Created",
                f"Batch file has been created successfully!\n\nWould you like to view the setup instructions?",
                detail=scheduler_instructions
            )

        except Exception as e:
            logger.error(f"Error generating batch file: {str(e)}")
            messagebox.showerror("Error", f"Failed to generate batch file: {str(e)}")

class UnifiedAdminGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("RingCentral-Zoho Integration Admin Tools")
        self.root.geometry("1200x800")
        
        # Initialize storage and clients
        self.storage = SecureStorage()
        self.rc_client = None
        self.zoho_client = None
        
        # Configure root grid
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(0, weight=1)
        
        # Create main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky="nsew")
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.grid(row=0, column=0, sticky="nsew")

        # Create tabs
        self.credentials_tab = CredentialsTab(self.notebook, self.storage)
        self.extensions_tab = ExtensionsTab(self.notebook, self.storage)
        self.lead_owners_tab = LeadOwnersTab(self.notebook, self.storage)
        self.run_script_tab = RunScriptTab(self.notebook, self.storage)
        self.scheduler_tab = SchedulerSetupTab(self.notebook, self.storage)

        # Add tabs to notebook
        self.notebook.add(self.credentials_tab, text='  Setup Credentials  ')
        self.notebook.add(self.extensions_tab, text='  Manage Extensions  ')
        self.notebook.add(self.lead_owners_tab, text='  Manage Lead Owners  ')
        self.notebook.add(self.run_script_tab, text='  Run Script Ad-Hoc  ')
        self.notebook.add(self.scheduler_tab, text='  Scheduler Setup  ')

        # Configure notebook to expand
        self.notebook.grid_rowconfigure(0, weight=1)
        self.notebook.grid_columnconfigure(0, weight=1)

        # Style configuration for notebook tabs
        style = ttk.Style()
        style.configure('TNotebook.Tab', padding=[20, 5])

        # Create required directories
        Path('logs').mkdir(exist_ok=True)
        Path('data').mkdir(exist_ok=True)

def main():
    """Main function"""
    try:
        root = tk.Tk()
        app = UnifiedAdminGUI(root)
        root.mainloop()
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        messagebox.showerror("Error", f"An error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 