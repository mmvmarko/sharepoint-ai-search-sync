#!/usr/bin/env python3
"""Explore SharePoint site structure to find the correct folder path."""

import msal
import requests
import os
import webbrowser
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
SITE_ID = os.getenv("SITE_ID")
SCOPES = ["https://graph.microsoft.com/Files.Read.All", "https://graph.microsoft.com/Sites.Read.All"]

def get_access_token():
    """Get access token using device code flow."""
    authority = f"https://login.microsoftonline.com/{TENANT_ID}"
    app = msal.PublicClientApplication(
        client_id=CLIENT_ID, 
        authority=authority,
        enable_pii_log=False
    )
    
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        print(f"Failed to create device flow: {flow}")
        return None
    
    print(f"{flow['message']}")
    
    # Auto-open browser
    if 'verification_uri' in flow:
        print(f"Opening browser...")
        webbrowser.open(flow['verification_uri'])
    
    result = app.acquire_token_by_device_flow(flow)
    
    if "access_token" in result:
        print("✅ Authentication successful!")
        return result["access_token"]
    else:
        print(f"❌ Authentication failed: {result.get('error_description')}")
        return None

def explore_site(access_token):
    """Explore SharePoint site structure."""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    
    print(f"\n=== Exploring Site: {SITE_ID} ===")
    
    # Get site info
    site_url = f"https://graph.microsoft.com/v1.0/sites/{SITE_ID}"
    response = requests.get(site_url, headers=headers)
    
    if response.status_code == 200:
        site_info = response.json()
        print(f"✅ Site found: {site_info.get('displayName', 'Unknown')}")
        print(f"   URL: {site_info.get('webUrl', 'Unknown')}")
    else:
        print(f"❌ Site access failed: {response.status_code} - {response.text}")
        return
    
    # Get drives
    drives_url = f"https://graph.microsoft.com/v1.0/sites/{SITE_ID}/drives"
    response = requests.get(drives_url, headers=headers)
    
    if response.status_code == 200:
        drives = response.json().get('value', [])
        print(f"\n=== Available Drives ({len(drives)}) ===")
        for drive in drives:
            print(f"  📁 {drive.get('name', 'Unnamed')} (ID: {drive.get('id', 'Unknown')})")
            print(f"     Type: {drive.get('driveType', 'Unknown')}")
            
            # Explore root of each drive
            if drive.get('id'):
                explore_drive_root(access_token, drive['id'], drive.get('name', 'Unnamed'))
    else:
        print(f"❌ Drives access failed: {response.status_code} - {response.text}")

def explore_drive_root(access_token, drive_id, drive_name):
    """Explore root of a specific drive."""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    
    root_url = f"https://graph.microsoft.com/v1.0/sites/{SITE_ID}/drives/{drive_id}/root/children"
    response = requests.get(root_url, headers=headers)
    
    if response.status_code == 200:
        items = response.json().get('value', [])
        print(f"\n  📂 Root contents of '{drive_name}' ({len(items)} items):")
        for item in items[:10]:  # Show first 10 items
            icon = "📁" if 'folder' in item else "📄"
            print(f"    {icon} {item.get('name', 'Unnamed')}")
            
            # If it's a folder that might contain our target documents
            if 'folder' in item and any(keyword in item.get('name', '').lower() 
                                      for keyword in ['document', 'general', 'user', 'guide']):
                explore_folder(access_token, drive_id, item['id'], item.get('name', 'Unnamed'), level=1)
                
        if len(items) > 10:
            print(f"    ... and {len(items) - 10} more items")
    else:
        print(f"    ❌ Root access failed: {response.status_code}")

def explore_folder(access_token, drive_id, folder_id, folder_name, level=0):
    """Explore a specific folder."""
    if level > 3:  # Limit recursion depth
        return
        
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    
    folder_url = f"https://graph.microsoft.com/v1.0/sites/{SITE_ID}/drives/{drive_id}/items/{folder_id}/children"
    response = requests.get(folder_url, headers=headers)
    
    if response.status_code == 200:
        items = response.json().get('value', [])
        indent = "  " * (level + 2)
        print(f"{indent}📂 Inside '{folder_name}' ({len(items)} items):")
        
        for item in items[:5]:  # Show first 5 items
            icon = "📁" if 'folder' in item else "📄"
            print(f"{indent}  {icon} {item.get('name', 'Unnamed')}")
            
            # Continue exploring relevant folders
            if 'folder' in item and level < 2 and any(keyword in item.get('name', '').lower() 
                                                    for keyword in ['general', 'user', 'guide']):
                explore_folder(access_token, drive_id, item['id'], item.get('name', 'Unnamed'), level + 1)
        
        if len(items) > 5:
            print(f"{indent}  ... and {len(items) - 5} more items")

if __name__ == "__main__":
    token = get_access_token()
    if token:
        explore_site(token)