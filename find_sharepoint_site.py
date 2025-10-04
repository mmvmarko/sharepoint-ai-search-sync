#!/usr/bin/env python3
"""Find the correct SharePoint site ID and structure."""

import msal
import requests
import os
import webbrowser
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
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

def find_sharepoint_sites(access_token):
    """Find SharePoint sites using different methods."""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    
    print("\n=== Method 1: Search for sites ===")
    search_url = "https://graph.microsoft.com/v1.0/sites?search=EXTiCoreSTB"
    response = requests.get(search_url, headers=headers)
    
    if response.status_code == 200:
        sites = response.json().get('value', [])
        print(f"Found {len(sites)} sites:")
        for site in sites:
            print(f"  📍 {site.get('displayName', 'Unknown')}")
            print(f"     ID: {site.get('id', 'Unknown')}")
            print(f"     URL: {site.get('webUrl', 'Unknown')}")
            print()
            
            # Try to get drives for this site
            if site.get('id'):
                get_site_drives(access_token, site['id'], site.get('displayName', 'Unknown'))
    else:
        print(f"❌ Search failed: {response.status_code} - {response.text}")
    
    print("\n=== Method 2: Try direct site access ===")
    # Try different site ID formats
    site_variations = [
        "comtradedoo.sharepoint.com,{site-id},b63bb74e-26b0-4c73-88de-da37e6b6d24e",
        "comtradedoo.sharepoint.com:/sites/EXTiCoreSTB",
        "comtradedoo.sharepoint.com,b63bb74e-26b0-4c73-88de-da37e6b6d24e,{site-id}"
    ]
    
    for site_id in site_variations:
        print(f"\nTrying site ID: {site_id}")
        site_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}"
        response = requests.get(site_url, headers=headers)
        
        if response.status_code == 200:
            site_info = response.json()
            print(f"✅ Success! Site: {site_info.get('displayName', 'Unknown')}")
            print(f"   Correct ID: {site_info.get('id', 'Unknown')}")
            get_site_drives(access_token, site_info.get('id'), site_info.get('displayName', 'Unknown'))
            break
        else:
            print(f"❌ Failed: {response.status_code}")

def get_site_drives(access_token, site_id, site_name):
    """Get drives for a specific site."""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    
    print(f"\n  📁 Drives in '{site_name}':")
    drives_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives"
    response = requests.get(drives_url, headers=headers)
    
    if response.status_code == 200:
        drives = response.json().get('value', [])
        for drive in drives:
            print(f"    📁 {drive.get('name', 'Unnamed')} (ID: {drive.get('id', 'Unknown')})")
            print(f"       Type: {drive.get('driveType', 'Unknown')}")
            
            # Explore this drive
            if drive.get('id'):
                explore_drive_structure(access_token, site_id, drive['id'], drive.get('name', 'Unnamed'))
    else:
        print(f"    ❌ Drives access failed: {response.status_code} - {response.text}")

def explore_drive_structure(access_token, site_id, drive_id, drive_name):
    """Explore the structure of a drive."""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    
    print(f"\n    📂 Contents of '{drive_name}':")
    root_url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drives/{drive_id}/root/children"
    response = requests.get(root_url, headers=headers)
    
    if response.status_code == 200:
        items = response.json().get('value', [])
        for item in items[:10]:  # Show first 10 items
            icon = "📁" if 'folder' in item else "📄"
            print(f"      {icon} {item.get('name', 'Unnamed')}")
            
            # Show path information for documents folder
            if 'folder' in item and 'document' in item.get('name', '').lower():
                path = f"/{item.get('name')}"
                print(f"         📍 Path for API: {path}")
                
        if len(items) > 10:
            print(f"      ... and {len(items) - 10} more items")
    else:
        print(f"      ❌ Root access failed: {response.status_code}")

if __name__ == "__main__":
    token = get_access_token()
    if token:
        find_sharepoint_sites(token)