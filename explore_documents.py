#!/usr/bin/env python3
"""Explore Documents drive to find user guides."""

import msal
import requests
import os
import webbrowser
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
SCOPES = ["https://graph.microsoft.com/Files.Read.All", "https://graph.microsoft.com/Sites.Read.All"]

# From previous exploration
SITE_ID = "comtradedoo.sharepoint.com,95bda638-a8aa-49b5-a295-fd15ef56bb89,75f737b9-e0af-4f09-b912-ac5f38bb0164"
DOCUMENTS_DRIVE_ID = "b!OKa9laqotUmilf0V71a7ibk393Wv4AlPuRKsXzi7AWQvvM34apAOT4tIeG6b92Qk"

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

def explore_documents_drive(access_token):
    """Explore the Documents drive for user guides."""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    
    print(f"\\n=== Exploring Documents Drive ===")
    
    # Get all folders in Documents drive
    root_url = f"https://graph.microsoft.com/v1.0/sites/{SITE_ID}/drives/{DOCUMENTS_DRIVE_ID}/root/children"
    response = requests.get(root_url, headers=headers)
    
    if response.status_code == 200:
        items = response.json().get('value', [])
        print(f"Found {len(items)} items in Documents:")
        
        # Look for folders that might contain user guides
        for item in items:
            if 'folder' in item:
                folder_name = item.get('name', 'Unnamed')
                print(f"📁 {folder_name}")
                
                # Check if this might contain user guides
                if any(keyword in folder_name.lower() for keyword in ['general', 'user', 'guide', 'doc', 'manual']):
                    print(f"   🎯 This might contain user guides - exploring...")
                    explore_folder(access_token, item['id'], folder_name, level=1)
                elif 'stb' in folder_name.lower():
                    print(f"   📋 STB-related folder - checking for guides...")
                    explore_folder(access_token, item['id'], folder_name, level=1)
    else:
        print(f"❌ Failed to access Documents drive: {response.status_code} - {response.text}")

def explore_folder(access_token, folder_id, folder_name, level=0):
    """Explore a specific folder."""
    if level > 2:  # Limit recursion
        return
        
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    
    folder_url = f"https://graph.microsoft.com/v1.0/sites/{SITE_ID}/drives/{DOCUMENTS_DRIVE_ID}/items/{folder_id}/children"
    response = requests.get(folder_url, headers=headers)
    
    if response.status_code == 200:
        items = response.json().get('value', [])
        indent = "   " * level
        print(f"{indent}📂 Inside '{folder_name}' ({len(items)} items):")
        
        for item in items[:10]:  # Show first 10 items
            icon = "📁" if 'folder' in item else "📄"
            item_name = item.get('name', 'Unnamed')
            print(f"{indent}  {icon} {item_name}")
            
            # Check for user guides in file names
            if 'file' in item and any(keyword in item_name.lower() for keyword in ['guide', 'manual', 'doc', 'instruction']):
                print(f"{indent}     🎯 USER GUIDE FOUND!")
                
            # Continue exploring relevant folders
            if 'folder' in item and level < 2:
                if any(keyword in item_name.lower() for keyword in ['general', 'user', 'guide', 'manual', 'doc']):
                    explore_folder(access_token, item['id'], item_name, level + 1)
        
        if len(items) > 10:
            print(f"{indent}  ... and {len(items) - 10} more items")
            
        # If this looks like a user guides folder, show the path
        if any(keyword in folder_name.lower() for keyword in ['general', 'user', 'guide']) and level <= 1:
            print(f"{indent}📍 Possible path: /{folder_name}")
            
    else:
        print(f"{indent}❌ Folder access failed: {response.status_code}")

def test_specific_paths(access_token):
    """Test specific paths that might exist."""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }
    
    print(f"\\n=== Testing Specific Paths ===")
    
    # Test various path combinations
    test_paths = [
        "",  # Root
        "/General",
        "/Documents",
        "/General/User Guides",
        "/EXT CT - STB Certification",
        "/EXT CT - STB migration"
    ]
    
    for path in test_paths:
        if path:
            url = f"https://graph.microsoft.com/v1.0/sites/{SITE_ID}/drives/{DOCUMENTS_DRIVE_ID}/root:{path}:/children"
        else:
            url = f"https://graph.microsoft.com/v1.0/sites/{SITE_ID}/drives/{DOCUMENTS_DRIVE_ID}/root/children"
            
        print(f"\\nTesting path: '{path}' (root if empty)")
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            items = response.json().get('value', [])
            print(f"✅ Found {len(items)} items")
            for item in items[:5]:
                icon = "📁" if 'folder' in item else "📄"
                print(f"  {icon} {item.get('name', 'Unnamed')}")
            if len(items) > 5:
                print(f"  ... and {len(items) - 5} more items")
        else:
            print(f"❌ Path not found: {response.status_code}")

if __name__ == "__main__":
    token = get_access_token()
    if token:
        explore_documents_drive(token)
        test_specific_paths(token)