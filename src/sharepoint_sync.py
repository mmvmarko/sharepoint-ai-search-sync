import os
import json
import time
import logging
from typing import Dict, Any, Iterator, Optional, Tuple
import requests
import msal
from azure.storage.blob import BlobServiceClient, BlobClient
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import AzureError, ClientAuthenticationError
from tenacity import retry, stop_after_attempt, wait_exponential
from config.settings import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SharePointSyncError(Exception):
    """Custom exception for SharePoint sync operations."""
    pass

class SharePointSync:
    """Handles SharePoint to Azure Blob sync operations with Service Principal authentication."""
    
    def __init__(self):
        self.config = config
        self.token = None
        self.token_expires_at = 0
        
        # Validate configuration
        if not self.config.validate_sharepoint_config():
            raise SharePointSyncError("SharePoint configuration is incomplete. Check your .env file.")
        if not self.config.validate_storage_config():
            raise SharePointSyncError("Azure Storage configuration is incomplete. Check your .env file.")
        
        # Initialize Azure Storage with Service Principal authentication
        self.credential = DefaultAzureCredential()
        self.blob_service_client = BlobServiceClient(
            account_url=self.config.az_storage_url,
            credential=self.credential
        )
        
        # Test storage access during initialization
        self._test_storage_access()
        logger.info("SharePointSync initialized with Service Principal authentication")
    
    def _test_storage_access(self):
        """Test Azure Storage access with current credentials."""
        try:
            # Try to get container properties to verify access
            container_client = self.blob_service_client.get_container_client(self.config.az_container)
            properties = container_client.get_container_properties()
            logger.info(f"✅ Storage access verified for container: {self.config.az_container}")
        except ClientAuthenticationError as e:
            logger.error(f"❌ Storage authentication failed: {e}")
            raise SharePointSyncError(
                "Storage authentication failed. Ensure your app registration has "
                "'Storage Blob Data Contributor' role on the storage account."
            )
        except Exception as e:
            logger.error(f"❌ Storage access test failed: {e}")
            raise SharePointSyncError(f"Storage access test failed: {e}")
    
    def get_token(self) -> str:
        """
        Get an access token using device code flow.
        Caches the token until it expires.
        """
        current_time = time.time()
        if self.token and current_time < self.token_expires_at:
            return self.token
            
        logger.info("Getting new access token...")
        app = msal.PublicClientApplication(
            self.config.client_id, 
            authority=self.config.authority
        )
        
        # Use device code flow for interactive authentication
        flow = app.initiate_device_flow(scopes=self.config.scopes)
        if "user_code" not in flow:
            raise SharePointSyncError(f"Failed to create device flow: {flow.get('error_description')}")
        
        print(f"\\n{flow['message']}\\n")
        print("Please complete the authentication in your browser...")
        
        result = app.acquire_token_by_device_flow(flow)
        if "access_token" not in result:
            error_desc = result.get("error_description", "Unknown error")
            raise SharePointSyncError(f"Authentication failed: {error_desc}")
        
        self.token = result["access_token"]
        # Set expiration time (subtract 5 minutes for safety)
        self.token_expires_at = current_time + result.get("expires_in", 3600) - 300
        
        logger.info("Successfully obtained access token")
        return self.token
    
    def load_delta_state(self) -> Dict[str, Any]:
        """Load delta state from file."""
        if os.path.exists(self.config.delta_state_file):
            try:
                with open(self.config.delta_state_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load delta state: {e}. Starting fresh sync.")
        return {}
    
    def save_delta_state(self, state: Dict[str, Any]) -> None:
        """Save delta state to file."""
        try:
            with open(self.config.delta_state_file, 'w') as f:
                json.dump(state, f, indent=2)
            logger.info(f"Saved delta state to {self.config.delta_state_file}")
        except IOError as e:
            logger.error(f"Failed to save delta state: {e}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def graph_get(self, url: str) -> Dict[str, Any]:
        """Make a GET request to Microsoft Graph API with retry logic."""
        token = self.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 401:
            # Token might have expired, get a new one
            self.token = None
            self.token_expires_at = 0
            token = self.get_token()
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(url, headers=headers)
        
        response.raise_for_status()
        return response.json()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def stream_download(self, download_url: str) -> Iterator[bytes]:
        """Download file content as a stream with retry logic."""
        token = self.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        
        with requests.get(download_url, headers=headers, stream=True) as response:
            if response.status_code == 401:
                # Token might have expired, get a new one
                self.token = None
                self.token_expires_at = 0
                token = self.get_token()
                headers = {"Authorization": f"Bearer {token}"}
                with requests.get(download_url, headers=headers, stream=True) as retry_response:
                    retry_response.raise_for_status()
                    for chunk in retry_response.iter_content(chunk_size=1024*1024):  # 1MB chunks
                        if chunk:
                            yield chunk
            else:
                response.raise_for_status()
                for chunk in response.iter_content(chunk_size=1024*1024):  # 1MB chunks
                    if chunk:
                        yield chunk
    
    def upload_blob(self, blob_key: str, content_stream: Iterator[bytes], metadata: Dict[str, str]) -> None:
        """Upload content to Azure Blob Storage with Service Principal authentication."""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.config.az_container,
                blob=blob_key
            )
            
            # Collect all chunks into bytes
            content_bytes = b"".join(content_stream)
            
            blob_client.upload_blob(
                data=content_bytes, 
                overwrite=True, 
                metadata=metadata
            )
            
            logger.info(f"Uploaded blob: {blob_key} ({len(content_bytes)} bytes)")
            
        except AzureError as e:
            logger.error(f"Failed to upload blob {blob_key}: {e}")
            raise SharePointSyncError(f"Blob upload failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error uploading {blob_key}: {e}")
            raise SharePointSyncError(f"Blob upload failed: {e}")
    
    def upload_sidecar(self, blob_key: str, sidecar_data: Dict[str, Any]) -> None:
        """Upload sidecar JSON file for better indexing."""
        try:
            sidecar_key = f"{blob_key}.json"
            sidecar_content = json.dumps(sidecar_data, indent=2).encode('utf-8')
            
            blob_client = self.blob_service_client.get_blob_client(
                container=self.config.az_container,
                blob=sidecar_key
            )
            
            blob_client.upload_blob(
                data=sidecar_content,
                overwrite=True,
                content_type="application/json"
            )
            
            logger.info(f"Uploaded sidecar: {sidecar_key}")
            
        except Exception as e:
            logger.error(f"Failed to upload sidecar for {blob_key}: {e}")
            # Don't raise here as sidecar is optional
    
    def get_safe_blob_key(self, parent_path: str, file_name: str) -> str:
        """Generate a safe blob key from SharePoint path and filename."""
        # Remove drive prefix from parent path
        if ":" in parent_path:
            rel_path = parent_path.split(":")[-1].strip("/")
        else:
            rel_path = parent_path.strip("/")
        
        # Combine path and filename
        if rel_path:
            return f"{rel_path}/{file_name}".replace("//", "/")
        else:
            return file_name
    
    def process_sharepoint_item(self, item: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Process a single SharePoint item (file).
        Returns (success, message).
        """
        try:
            # Skip folders
            if item.get("folder"):
                return True, "Skipped folder"
            
            name = item["name"]
            web_url = item["webUrl"]
            item_id = item["id"]
            
            # Build blob key
            parent_ref = item.get("parentReference", {})
            parent_path = parent_ref.get("path", "")
            blob_key = self.get_safe_blob_key(parent_path, name)
            
            logger.info(f"Processing file: {name} -> {blob_key}")
            
            # Get download URL
            drive_id = parent_ref.get("driveId", self.config.drive_id)
            content_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/content"
            
            # Download file content
            content_stream = self.stream_download(content_url)
            
            # Prepare blob metadata (Azure requires lowercase keys)
            metadata = {
                "source_url": web_url,
                "sp_item_id": item_id,
                "sp_drive_id": drive_id,
                "sp_etag": item.get("eTag", ""),
                "sp_mtime": item.get("lastModifiedDateTime", ""),
                "sp_file_name": name
            }
            
            # Upload to blob storage
            self.upload_blob(blob_key, content_stream, metadata)
            
            # Create and upload sidecar JSON
            sidecar_data = {
                "originalUrl": web_url,
                "name": name,
                "lastModified": item.get("lastModifiedDateTime"),
                "size": item.get("size"),
                "sharepointIds": item.get("sharepointIds", {}),
                "blobKey": blob_key
            }
            self.upload_sidecar(blob_key, sidecar_data)
            
            return True, f"Successfully processed {name}"
            
        except Exception as e:
            error_msg = f"Failed to process {item.get('name', 'unknown')}: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def sync_sharepoint_folder(self) -> Dict[str, Any]:
        """
        Sync SharePoint folder to Azure Blob Storage using delta API.
        Returns summary of the sync operation.
        """
        logger.info("Starting SharePoint folder sync...")
        
        # Load delta state
        state = self.load_delta_state()
        
        # Build initial delta URL
        delta_url = state.get("delta_url")
        if not delta_url:
            delta_url = (
                f"https://graph.microsoft.com/v1.0/sites/{self.config.site_id}/"
                f"drives/{self.config.drive_id}/root:/{self.config.folder_path}:/delta"
            )
            logger.info("Starting full sync (no previous delta state)")
        else:
            logger.info("Continuing incremental sync from previous state")
        
        total_files = 0
        processed_files = 0
        errors = []
        
        try:
            while delta_url:
                logger.info(f"Fetching delta page: {delta_url}")
                data = self.graph_get(delta_url)
                
                items = data.get("value", [])
                total_files += len([item for item in items if not item.get("folder")])
                
                for item in items:
                    if not item.get("folder"):  # Process only files
                        success, message = self.process_sharepoint_item(item)
                        if success:
                            processed_files += 1
                        else:
                            errors.append(message)
                
                # Get next URL
                delta_url = data.get("@odata.nextLink")
                
                # If this is the final page, save the delta link
                if "@odata.deltaLink" in data:
                    final_delta_url = data["@odata.deltaLink"]
                    self.save_delta_state({"delta_url": final_delta_url})
                    logger.info("Sync completed. Delta state saved for next run.")
                    break
        
        except Exception as e:
            error_msg = f"Sync failed: {e}"
            logger.error(error_msg)
            errors.append(error_msg)
        
        # Return summary
        summary = {
            "total_files": total_files,
            "processed_files": processed_files,
            "errors": errors,
            "success_rate": (processed_files / total_files * 100) if total_files > 0 else 0
        }
        
        logger.info(f"Sync summary: {processed_files}/{total_files} files processed successfully")
        if errors:
            logger.warning(f"{len(errors)} errors occurred during sync")
        
        return summary