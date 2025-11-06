"""
Simple blob uploader using storage account key from .env

Usage:
    python simple_upload.py swagger
    python simple_upload.py code
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient, ContentSettings

# Load .env
load_dotenv()

def get_content_type(file_path: str) -> str:
    """Determine content type based on file extension."""
    ext = Path(file_path).suffix.lower()
    content_types = {
        '.json': 'application/json',
        '.txt': 'text/plain',
        '.md': 'text/markdown',
    }
    return content_types.get(ext, 'text/plain')


def upload_files(folder_type: str):
    """Upload swagger or code files to blob storage."""
    
    # Get storage account info from .env
    storage_url = os.getenv('AZ_STORAGE_URL')
    storage_key = os.getenv('AZ_STORAGE_ACCOUNT_KEY')
    
    if not storage_url or not storage_key:
        print("❌ Missing AZ_STORAGE_URL or AZ_STORAGE_ACCOUNT_KEY in .env")
        sys.exit(1)
    
    # Extract account name
    account_name = storage_url.split('//')[1].split('.')[0]
    
    # Build connection string
    conn_str = f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey={storage_key};EndpointSuffix=core.windows.net"
    
    # Determine source and container
    if folder_type == 'swagger':
        source_dir = Path('bo_prepared/swagger')
        container_name = 'bo-swagger'
    elif folder_type == 'code':
        source_dir = Path('bo_prepared/code')
        container_name = 'bo-code'
    else:
        print(f"❌ Invalid folder type. Use 'swagger' or 'code'")
        sys.exit(1)
    
    if not source_dir.exists():
        print(f"❌ Source directory not found: {source_dir}")
        sys.exit(1)
    
    print(f"📦 Uploading {folder_type} files to container '{container_name}'...")
    print(f"   Storage: {account_name}")
    print(f"   Source: {source_dir}\n")
    
    # Create blob service client
    blob_service_client = BlobServiceClient.from_connection_string(conn_str)
    
    # Get or create container
    container_client = blob_service_client.get_container_client(container_name)
    try:
        container_client.get_container_properties()
        print(f"✅ Container '{container_name}' exists\n")
    except:
        print(f"📦 Creating container '{container_name}'...")
        container_client.create_container()
        print(f"✅ Container created\n")
    
    # Upload files
    files = list(source_dir.glob('*'))
    files = [f for f in files if f.is_file()]
    
    uploaded = 0
    for file_path in files:
        blob_name = file_path.name
        content_type = get_content_type(str(file_path))
        
        blob_client = container_client.get_blob_client(blob_name)
        
        with open(file_path, 'rb') as data:
            blob_client.upload_blob(
                data,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type)
            )
        
        print(f"  ✅ {blob_name}")
        uploaded += 1
    
    print(f"\n{'='*70}")
    print(f"✅ Upload complete: {uploaded} files uploaded to '{container_name}'")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in ['swagger', 'code']:
        print("Usage: python simple_upload.py [swagger|code]")
        sys.exit(1)
    
    upload_files(sys.argv[1])
