#!/usr/bin/env python3
"""Simple test for device code authentication."""

import msal
import os
import webbrowser
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
SCOPES = ["https://graph.microsoft.com/Files.Read.All", "https://graph.microsoft.com/Sites.Read.All"]

def test_device_flow():
    """Test device code flow authentication."""
    print(f"Testing device flow with:")
    print(f"  Tenant ID: {TENANT_ID}")
    print(f"  Client ID: {CLIENT_ID}")
    print(f"  Scopes: {SCOPES}")
    print()
    
    authority = f"https://login.microsoftonline.com/{TENANT_ID}"
    # Create public client app - device code flow requires public client configuration
    app = msal.PublicClientApplication(
        client_id=CLIENT_ID, 
        authority=authority,
        # Enable device flow capabilities
        enable_pii_log=False
    )
    
    print("Initiating device flow...")
    flow = app.initiate_device_flow(scopes=SCOPES)
    
    if "user_code" not in flow:
        print("❌ Failed to create device flow")
        print(f"Error: {flow}")
        return None
    
    print("✅ Device flow created successfully!")
    print(f"Message: {flow['message']}")
    print()
    
    # Automatically open browser
    if 'verification_uri' in flow:
        print(f"Opening browser to: {flow['verification_uri']}")
        webbrowser.open(flow['verification_uri'])
    
    print("Please complete authentication in your browser...")
    print(f"User Code: {flow.get('user_code', 'N/A')}")
    print("Waiting for authentication...")
    
    result = app.acquire_token_by_device_flow(flow)
    
    if "access_token" in result:
        print("✅ Authentication successful!")
        print(f"Token type: {result.get('token_type', 'unknown')}")
        print(f"Expires in: {result.get('expires_in', 'unknown')} seconds")
        return result["access_token"]
    else:
        print("❌ Authentication failed!")
        print(f"Error: {result.get('error_description', 'Unknown error')}")
        return None

if __name__ == "__main__":
    test_device_flow()