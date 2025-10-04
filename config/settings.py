import os
from typing import Optional
import os
import logging
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)
from dotenv import load_dotenv

load_dotenv()

class Config(BaseSettings):
    """Configuration settings for the SharePoint to Azure AI Search sync application."""
    
    # Azure AD Configuration
    tenant_id: str = os.getenv("TENANT_ID", "")
    client_id: str = os.getenv("CLIENT_ID", "")
    client_secret: str = os.getenv("CLIENT_SECRET", "")
    
    # SharePoint Configuration
    site_id: str = os.getenv("SITE_ID", "")
    drive_id: str = os.getenv("DRIVE_ID", "")
    folder_path: str = os.getenv("FOLDER_PATH", "Shared Documents")
    
    # Azure Storage Configuration (Service Principal)
    az_storage_url: str = os.getenv("AZ_STORAGE_URL", "")
    az_container: str = os.getenv("AZ_CONTAINER", "spofiles")
    az_storage_account_key: str = os.getenv("AZ_STORAGE_ACCOUNT_KEY", "")
    
    # Azure AI Search Configuration
    search_service_name: str = os.getenv("SEARCH_SERVICE_NAME", "")
    search_api_key: str = os.getenv("SEARCH_API_KEY", "")
    search_endpoint: str = os.getenv("SEARCH_ENDPOINT", "")
    
    # Azure OpenAI Configuration (Required for vector embeddings)
    azure_openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_openai_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    azure_openai_embedding_model: str = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    
    # Application Settings
    delta_state_file: str = "delta_state.json"
    scopes: list = ["https://graph.microsoft.com/Files.Read.All", "https://graph.microsoft.com/Sites.Read.All"]
    
    @property
    def authority(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}"
    
    @property
    def storage_connection_string(self) -> str:
        """Generate storage connection string for Azure AI Search data source."""
        if not self.az_storage_url:
            return ""
        account_name = self.az_storage_url.split("//")[1].split(".")[0]
        return f"DefaultEndpointsProtocol=https;AccountName={account_name};AccountKey=[managed-identity]"
    
    @property
    def storage_account_name(self) -> str:
        """Extract storage account name from URL."""
        if not self.az_storage_url:
            return ""
        return self.az_storage_url.split("//")[1].split(".")[0]
    
    def validate_sharepoint_config(self) -> bool:
        """Validate that required SharePoint configuration is present."""
        required_fields = [self.tenant_id, self.client_id, self.site_id, self.drive_id]
        return all(field.strip() for field in required_fields)
    
    def validate_storage_config(self) -> bool:
        """Validate that required Azure Storage configuration is present."""
        required_fields = [self.az_storage_url, self.az_container]
        if not all(field.strip() for field in required_fields):
            return False
        
        # Validate storage URL format
        if not self.az_storage_url.startswith("https://") or ".blob.core.windows.net" not in self.az_storage_url:
            return False
        
        return True
    
    def validate_storage_for_search(self) -> bool:
        """Validate storage configuration for Azure AI Search data source."""
        if not self.validate_storage_config():
            return False
        
        # For Azure AI Search, we need either account key or proper managed identity setup
        has_account_key = self.az_storage_account_key and self.az_storage_account_key != "your_storage_account_key_here"
        if not has_account_key:
            # If no account key, warn about managed identity requirements
            logger.warning("No storage account key provided. Azure AI Search data source will require:")
            logger.warning("1. Search service must have system-assigned managed identity enabled")
            logger.warning("2. Managed identity must have 'Storage Blob Data Reader' role on storage account")
        
        return True
    
    def validate_search_config(self) -> bool:
        """Validate that required Azure AI Search configuration is present."""
        required_fields = [self.search_service_name, self.search_api_key, self.search_endpoint]
        return all(field.strip() for field in required_fields)
    
    def validate_openai_config(self) -> bool:
        """Validate that required Azure OpenAI configuration is present."""
        required_fields = [self.azure_openai_endpoint, self.azure_openai_api_key]
        return all(field.strip() for field in required_fields)
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global configuration instance
config = Config()