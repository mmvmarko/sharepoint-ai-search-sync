# SharePoint to Azure AI Search Sync Configuration

This directory contains configuration files for the application.

## Files

- `settings.py`: Main configuration class that loads environment variables
- `.env.template`: Template for environment variables (copy to `.env`)

## Setup

1. Copy `.env.template` to `.env`
2. Fill in your Azure and SharePoint configuration values
3. The application will automatically load these settings

## Required Configuration

### Azure AD App Registration
- `TENANT_ID`: Your Azure AD tenant ID
- `CLIENT_ID`: Your Azure AD app registration client ID (use public client type)

### SharePoint
- `SITE_ID`: SharePoint site ID (format: contoso.sharepoint.com,<guid>,<guid>)
- `DRIVE_ID`: Document library drive ID
- `FOLDER_PATH`: Path to the folder you want to sync

### Azure Storage
- `AZ_STORAGE_URL`: Your blob storage account URL
- `AZ_CONTAINER`: Container name for storing files
- `AZ_SAS`: SAS token with read/write permissions

### Azure AI Search
- `SEARCH_SERVICE_NAME`: Name of your search service
- `SEARCH_API_KEY`: Admin API key for the search service
- `SEARCH_ENDPOINT`: Full endpoint URL to your search service

### Azure OpenAI (Required)
- `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI service endpoint
- `AZURE_OPENAI_API_KEY`: API key for Azure OpenAI service
- `AZURE_OPENAI_EMBEDDING_MODEL`: Embedding model name (default: text-embedding-3-small)