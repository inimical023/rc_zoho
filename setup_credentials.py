import argparse
import logging
import os
import sys
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from common import setup_logging

# Configure logging
logger = setup_logging('setup_credentials')

class SetupError(Exception):
    """Custom exception for setup errors"""
    def __init__(self, code, message, details=None):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(f"Error {code}: {message}")

def ensure_venv_activated():
    """Ensure virtual environment is activated"""
    if not hasattr(sys, 'real_prefix') and not hasattr(sys, 'base_prefix'):
        logger.info("Virtual environment not activated, attempting to activate...")
        venv_path = Path('.venv/Scripts/activate.bat')
        if not venv_path.exists():
            raise SetupError(
                code="VENV001",
                message="Virtual environment not found",
                details=f"Expected path: {venv_path}"
            )
        try:
            subprocess.run([str(venv_path)], shell=True, check=True)
            logger.info("Virtual environment activated successfully")
            return True
        except subprocess.CalledProcessError as e:
            raise SetupError(
                code="VENV002",
                message="Failed to activate virtual environment",
                details=str(e)
            )
    return True

class CredentialsGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("API Credentials Setup")
        self.root.geometry("600x800")

        # Create main frame with padding
        main_frame = ttk.Frame(root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # RingCentral Section
        rc_frame = ttk.LabelFrame(main_frame, text="RingCentral Credentials", padding="10")
        rc_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

        ttk.Label(rc_frame, text="JWT Token:").grid(row=0, column=0, sticky=tk.W)
        self.rc_jwt = ttk.Entry(rc_frame, width=50, show="*")
        self.rc_jwt.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        self.rc_jwt.bind('<KeyRelease>', self.validate_fields)

        ttk.Label(rc_frame, text="Client ID:").grid(row=1, column=0, sticky=tk.W)
        self.rc_id = ttk.Entry(rc_frame, width=50)
        self.rc_id.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        self.rc_id.bind('<KeyRelease>', self.validate_fields)

        ttk.Label(rc_frame, text="Client Secret:").grid(row=2, column=0, sticky=tk.W)
        self.rc_secret = ttk.Entry(rc_frame, width=50, show="*")
        self.rc_secret.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5)
        self.rc_secret.bind('<KeyRelease>', self.validate_fields)

        ttk.Label(rc_frame, text="Account ID:").grid(row=3, column=0, sticky=tk.W)
        self.rc_account = ttk.Entry(rc_frame, width=50)
        self.rc_account.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=5)
        self.rc_account.insert(0, "~")
        self.rc_account.bind('<KeyRelease>', self.validate_fields)

        rc_buttons_frame = ttk.Frame(rc_frame)
        rc_buttons_frame.grid(row=4, column=0, columnspan=2, pady=10)

        ttk.Button(rc_buttons_frame, text="Verify RingCentral", command=self.verify_rc).pack(side=tk.LEFT, padx=5)
        ttk.Button(rc_buttons_frame, text="Check Existing", command=self.check_rc).pack(side=tk.LEFT, padx=5)

        # Zoho Section
        zoho_frame = ttk.LabelFrame(main_frame, text="Zoho Credentials", padding="10")
        zoho_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)

        ttk.Label(zoho_frame, text="Client ID:").grid(row=0, column=0, sticky=tk.W)
        self.zoho_id = ttk.Entry(zoho_frame, width=50)
        self.zoho_id.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        self.zoho_id.bind('<KeyRelease>', self.validate_fields)

        ttk.Label(zoho_frame, text="Client Secret:").grid(row=1, column=0, sticky=tk.W)
        self.zoho_secret = ttk.Entry(zoho_frame, width=50, show="*")
        self.zoho_secret.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5)
        self.zoho_secret.bind('<KeyRelease>', self.validate_fields)

        ttk.Label(zoho_frame, text="Refresh Token:").grid(row=2, column=0, sticky=tk.W)
        self.zoho_refresh = ttk.Entry(zoho_frame, width=50, show="*")
        self.zoho_refresh.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5)
        self.zoho_refresh.bind('<KeyRelease>', self.validate_fields)

        zoho_buttons_frame = ttk.Frame(zoho_frame)
        zoho_buttons_frame.grid(row=3, column=0, columnspan=2, pady=10)

        ttk.Button(zoho_buttons_frame, text="Verify Zoho", command=self.verify_zoho).pack(side=tk.LEFT, padx=5)
        ttk.Button(zoho_buttons_frame, text="Check Existing", command=self.check_zoho).pack(side=tk.LEFT, padx=5)

        # Submit Button
        self.submit_button = ttk.Button(main_frame, text="Submit", command=self.submit_credentials)
        self.submit_button.grid(row=2, column=0, columnspan=2, pady=20)
        self.submit_button.state(['disabled'])

        # Load existing credentials if available
        self.load_existing_credentials()
        
        # Initial validation
        self.validate_fields()

    def validate_fields(self, event=None):
        """Validate all fields and enable/disable submit button accordingly"""
        rc_valid = all([
            self.rc_jwt.get().strip(),
            self.rc_id.get().strip(),
            self.rc_secret.get().strip(),
            self.rc_account.get().strip()
        ])
        
        zoho_valid = all([
            self.zoho_id.get().strip(),
            self.zoho_secret.get().strip(),
            self.zoho_refresh.get().strip()
        ])
        
        if rc_valid and zoho_valid:
            self.submit_button.state(['!disabled'])
        else:
            self.submit_button.state(['disabled'])

    def verify_rc(self):
        """Verify RingCentral credentials"""
        if not all([self.rc_jwt.get(), self.rc_id.get(), self.rc_secret.get(), self.rc_account.get()]):
            messagebox.showerror("Error", "Please fill in all RingCentral fields")
            return
        messagebox.showinfo("Success", "RingCentral credentials verified")

    def verify_zoho(self):
        """Verify Zoho credentials and refresh the token if needed"""
        if not all([self.zoho_id.get(), self.zoho_secret.get(), self.zoho_refresh.get()]):
            messagebox.showerror("Error", "Please fill in all Zoho fields")
            return
        
        try:
            # Attempt to refresh the Zoho token as a verification step
            import requests
            
            refresh_url = "https://accounts.zoho.com/oauth/v2/token"
            payload = {
                'refresh_token': self.zoho_refresh.get(),
                'client_id': self.zoho_id.get(),
                'client_secret': self.zoho_secret.get(),
                'grant_type': 'refresh_token'
            }
            
            response = requests.post(refresh_url, data=payload)
            
            if response.status_code == 200:
                data = response.json()
                if 'access_token' in data:
                    # Success - we have a valid token
                    messagebox.showinfo("Success", "Zoho credentials verified successfully")
                    # Store the new access token if needed
                    # self.zoho_access = data['access_token']
                    return True
            else:
                error_msg = f"Failed to verify Zoho credentials: {response.text}"
                logger.error(error_msg)
                messagebox.showerror("Error", "Zoho credentials verification failed. Please check your client ID, secret, and refresh token.")
                return False
            
        except Exception as e:
            logger.error(f"Error verifying Zoho credentials: {str(e)}")
            messagebox.showerror("Error", f"Failed to verify Zoho credentials: {str(e)}")
            return False

    def check_rc(self):
        """Check existing RingCentral credentials"""
        try:
            from secure_credentials import SecureCredentials
            creds = SecureCredentials()
            rc_creds = creds.get_rc_credentials()
            if rc_creds:
                messagebox.showinfo("Existing RingCentral Credentials",
                    f"JWT: {rc_creds['jwt'][:4]}...\n"
                    f"Client ID: {rc_creds['client_id'][:4]}...\n"
                    f"Client Secret: {rc_creds['client_secret'][:4]}...\n"
                    f"Account ID: {rc_creds['account_id']}")
            else:
                messagebox.showinfo("No Existing Credentials", "No RingCentral credentials found")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to check RingCentral credentials: {str(e)}")

    def check_zoho(self):
        """Check existing Zoho credentials"""
        try:
            from secure_credentials import SecureCredentials
            creds = SecureCredentials()
            zoho_creds = creds.get_zoho_credentials()
            if zoho_creds:
                messagebox.showinfo("Existing Zoho Credentials",
                    f"Client ID: {zoho_creds['client_id'][:4]}...\n"
                    f"Client Secret: {zoho_creds['client_secret'][:4]}...\n"
                    f"Refresh Token: {zoho_creds['refresh_token'][:4]}...")
            else:
                messagebox.showinfo("No Existing Credentials", "No Zoho credentials found")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to check Zoho credentials: {str(e)}")

    def load_existing_credentials(self):
        """Load existing credentials into the form"""
        try:
            from secure_credentials import SecureCredentials
            creds = SecureCredentials()
            rc_creds = creds.get_rc_credentials()
            zoho_creds = creds.get_zoho_credentials()

            if rc_creds:
                self.rc_jwt.insert(0, rc_creds['jwt'])
                self.rc_id.insert(0, rc_creds['client_id'])
                self.rc_secret.insert(0, rc_creds['client_secret'])
                self.rc_account.insert(0, rc_creds['account_id'])

            if zoho_creds:
                self.zoho_id.insert(0, zoho_creds['client_id'])
                self.zoho_secret.insert(0, zoho_creds['client_secret'])
                self.zoho_refresh.insert(0, zoho_creds['refresh_token'])

        except Exception as e:
            logger.error("Failed to load existing credentials: %s", e)

    def submit_credentials(self):
        """Submit credentials to secure storage"""
        try:
            from secure_credentials import SecureCredentials
            creds = SecureCredentials()

            # Save RingCentral credentials
            creds.save_rc_credentials(
                jwt=self.rc_jwt.get(),
                client_id=self.rc_id.get(),
                client_secret=self.rc_secret.get(),
                account_id=self.rc_account.get()
            )

            # Save Zoho credentials
            creds.save_zoho_credentials(
                client_id=self.zoho_id.get(),
                client_secret=self.zoho_secret.get(),
                refresh_token=self.zoho_refresh.get()
            )

            messagebox.showinfo("Success", "Credentials saved successfully!")
            self.root.quit()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to save credentials: {str(e)}")

def main():
    """Main function"""
    if not ensure_venv_activated():
        messagebox.showerror("Error", "Failed to activate virtual environment")
        return

    root = tk.Tk()
    app = CredentialsGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 