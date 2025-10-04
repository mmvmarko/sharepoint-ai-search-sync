# SharePoint to Azure AI Search Sync

A Python application that syncs SharePoint Online documents to Azure Blob Storage and configures Azure AI Search for powerful document search and retrieval, specifically designed to work with Microsoft Copilot Studio.

## Features

- **Service Principal Authentication**: Secure authentication using Azure Identity instead of SAS tokens
- **Incremental Sync**: Uses SharePoint delta API to efficiently track and sync only changed files
- **Azure Blob Storage**: Stores documents with rich metadata including original SharePoint URLs
- **Azure AI Search with Vector Embeddings**: Full-text search with semantic vector search for enhanced relevance
- **Copilot Studio Ready**: Preserves SharePoint URLs for proper citation links
- **User Authentication**: Uses delegated authentication (device code flow) for secure access
- **Robust Error Handling**: Comprehensive logging and error recovery
- **Configurable**: Easy setup through environment variables

## Prerequisites

- Python 3.8 or higher
- Azure subscription with:
  - Azure Storage Account
  - Azure AI Search service (Standard tier recommended)
  - Azure OpenAI service (required for vector embeddings)
- Azure AD App Registration (public client)
- SharePoint Online with appropriate permissions

## Quick Start

### 1. Clone and Install

```bash
cd sharepoint-ai-search-sync
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy the template and edit with your values
cp .env.template .env
# Edit .env with your Azure and SharePoint configuration
```

### 3. Check Configuration

```bash
python main.py config-info
```

### 4. Run Complete Setup

```bash
# Set up everything in one command
python main.py full-setup
```

Or run step by step:

```bash
# 1. Set up Azure AI Search pipeline
python main.py setup-search

# 2. Sync SharePoint content
python main.py sync

# 3. Run indexer to process documents
python main.py run-indexer
```

## Detailed Setup

### Azure AD App Registration

1. Go to Azure Portal → Azure Active Directory → App registrations
2. Create a new registration:
   - Name: "SharePoint AI Search Sync"
   - Supported account types: "Accounts in this organizational directory only"
   - **Public client/native**: Yes (important for device code flow)
3. Note the **Application (client) ID** and **Directory (tenant) ID**
4. Go to **API permissions** and add:
   - Microsoft Graph → Delegated → `Files.Read.All`
   - Microsoft Graph → Delegated → `Sites.Read.All`
5. Grant admin consent if required

### SharePoint Configuration

You need to identify your SharePoint site and document library:

```bash
# Get site ID (replace with your SharePoint URL)
# https://graph.microsoft.com/v1.0/sites/{hostname}:{site-path}

# Example for https://contoso.sharepoint.com/sites/documents:
# GET https://graph.microsoft.com/v1.0/sites/contoso.sharepoint.com:/sites/documents:

# Get drive ID for document library:
# GET https://graph.microsoft.com/v1.0/sites/{site-id}/drives
```

### Azure Storage Setup

1. Create a Storage Account in Azure Portal
2. Create a container (e.g., "spofiles")
3. **Assign Role to App Registration**:
   - Go to Storage Account > Access Control (IAM)
   - Add role assignment: **Storage Blob Data Contributor**
   - Assign to your Azure AD app registration
   - No SAS token needed - uses Service Principal authentication

### Azure AI Search Setup

1. Create an Azure AI Search service (Standard tier recommended)
2. Note the service name and admin API key
3. Ensure your IP is allowed if using firewall restrictions

### Azure OpenAI (Required for Vector Search)

1. Create Azure OpenAI resource
2. Deploy `text-embedding-3-small` model
3. Note the endpoint and API key

## Configuration Reference

Create a `.env` file based on `.env.template`:

```env
# Azure AD Configuration
TENANT_ID=your-tenant-id
CLIENT_ID=your-app-client-id

# SharePoint Configuration  
SITE_ID=contoso.sharepoint.com,{site-guid},{web-guid}
DRIVE_ID=drive-guid-for-document-library
FOLDER_PATH=Shared Documents/YourFolder

# Azure Storage Configuration (Service Principal Authentication)
AZ_STORAGE_URL=https://yourstorageaccount.blob.core.windows.net
AZ_CONTAINER=spofiles
# Note: No SAS token needed - using Service Principal authentication
# Ensure your app registration has "Storage Blob Data Contributor" role

# Azure AI Search Configuration
SEARCH_SERVICE_NAME=your-search-service
SEARCH_API_KEY=your-admin-key
SEARCH_ENDPOINT=https://your-search-service.search.windows.net

# Azure OpenAI Configuration (Required for vector embeddings)
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com
AZURE_OPENAI_API_KEY=your-openai-key
AZURE_OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

## Usage

### Command Line Interface

```bash
# Show help
python main.py --help

# Check configuration
python main.py config-info

# Full automated setup
python main.py full-setup

# Individual operations
python main.py sync                    # Sync SharePoint to blob storage
python main.py setup-search           # Set up search pipeline with vector embeddings
python main.py run-indexer            # Process documents in search
python main.py indexer-status         # Check indexer progress
python main.py list-resources         # List search resources
```

### Sync Process Details

1. **Authentication**: Uses device code flow for interactive sign-in
2. **Delta Tracking**: Maintains state in `delta_state.json` for incremental syncs
3. **File Processing**: Downloads files and uploads to blob with metadata
4. **Metadata**: Stores SharePoint URL and properties for proper citations
5. **Sidecar Files**: Creates `.json` sidecars for reliable indexing

### Search Pipeline Components

1. **Data Source**: Points to your blob container
2. **Skillset**: Extracts entities and generates vector embeddings using Azure OpenAI
3. **Index**: Defines searchable fields including `source_url` for citations and `contentVector` for semantic search
4. **Indexer**: Processes documents on a schedule (every 30 minutes)

## Copilot Studio Integration

1. In Copilot Studio, go to your agent settings
2. Add knowledge source → Azure AI Search
3. Select your search service and index
4. **Important**: Map the `source_url` field for proper citations
5. Test that answers include clickable SharePoint links

## Monitoring and Troubleshooting

### Check Sync Status

```bash
# View sync logs
tail -f sync.log

# Check delta state
cat delta_state.json
```

### Monitor Indexer

```bash
# Check indexer status
python main.py indexer-status

# View search service resources
python main.py list-resources
```

### Common Issues

1. **Storage Authentication Fails**:
   - Verify your app registration has `Storage Blob Data Contributor` role
   - Check that you're signed in with the correct account
   - Ensure storage account allows the authentication method
4. **Search Setup Failed**: Verify search service admin key and endpoint
5. **No Citations in Copilot**: Ensure `source_url` field mapping in Copilot Studio

### Debug Mode

```bash
# Enable detailed logging
python main.py --debug sync
```

## Architecture

```
SharePoint Online
       ↓ (Microsoft Graph Delta API)
Python Sync App
       ↓ (Azure Storage SDK)
Azure Blob Storage + Metadata
       ↓ (Azure AI Search Indexer)
Azure AI Search Index
       ↓ (REST API)
Copilot Studio Agent
```

## File Structure

```
sharepoint-ai-search-sync/
├── main.py                 # Main CLI application
├── requirements.txt        # Python dependencies
├── .env.template          # Configuration template
├── config/
│   ├── settings.py        # Configuration management
│   └── README.md          # Config documentation
├── src/
│   ├── sharepoint_sync.py # SharePoint sync logic
│   └── azure_search_setup.py # Search setup logic
└── scripts/
    └── search_manager.py  # Additional search utilities
```

## Security Considerations

- Uses delegated authentication (respects SharePoint permissions)
- **Service Principal authentication** for Azure Storage (no SAS tokens)
- Store sensitive config in Azure Key Vault for production
- Use managed identity in production deployments
- Monitor access logs for unusual activity

## Production Recommendations

1. **Automation**: Run sync via Azure Functions or Logic Apps
2. **Monitoring**: Set up alerts for failed sync operations
3. **Backup**: Implement backup strategy for delta state
4. **Security**: Use managed identity and Key Vault
5. **Performance**: Consider file type filtering and size limits
6. **Compliance**: Ensure data handling meets organizational requirements

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review logs in `sync.log`
3. Validate configuration with `python main.py config-info`
4. Test individual components step by step

## License

This project is provided as-is for educational and demonstration purposes.