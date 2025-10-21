# SharePoint to Azure AI Search Sync

A Python application that syncs SharePoint Online documents to Azure Blob Storage and configures Azure AI Search for powerful document search and retrieval, specifically designed to work with Microsoft Copilot Studio.

> For a full operational walkthrough (workflows, command glossary, troubleshooting), see **[guide.md](./guide.md)**.
> 
> **NEW**: For automated vertical creation with intelligent file analysis, see **[INTELLIGENT_VERTICALS.md](./INTELLIGENT_VERTICALS.md)**.

## Features

- **Service Principal Authentication**: Secure authentication using Azure Identity instead of SAS tokens
- **Incremental Sync**: Uses SharePoint delta API to efficiently track and sync only changed files
- **Azure Blob Storage**: Stores documents with rich metadata including original SharePoint URLs
- **Azure AI Search with Vector Embeddings**: Full-text search with semantic vector search for enhanced relevance
- **Integrated Vectorization Mode**: Optional simplified pipeline using Azure AI Search vectorizers + embedding skill for Copilot Studio compatibility
- **🆕 Intelligent Vertical Creator**: Automatically analyzes source files and suggests optimal vertical configurations (chunking, splitting, grouping)
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
python main.py run-indexer ix-pp-portal
python main.py run-indexer ix-pp-portal-json
# Aliases also work:
python main.py run_indexer ix-pp-portal-json
```

### Modern Integrated Vectorization Path (Recommended)

If you want a Copilot Studio–ready vector index using integrated vectorization:

```bash
# 1. Sync SharePoint content to Blob (initial or incremental)
# - access to SPO folder: on behalf ob logged in user, for example marko.vuckovic@comtradegaming.com
# - uploading files to Blob: storage account key
python main.py sync

# 2. Create/update stable vertical (ds/ss/idx/ix all with prefix 'spo') and start indexer
# -admin API key
python main.py create_vertical --prefix spo

python main.py indexer-status ix-pp-portal
python main.py indexer-status ix-pp-portal-json
# Or
python main.py indexer_status ix-pp-portal-json

# (Optional) Run a disposable test vertical
python main.py test_integrated --prefix demo

# (Cleanup) Delete a vertical
python main.py delete_vertical --prefix demo
```

Then add `idx-spo` as a knowledge source in Copilot Studio.

### Quickly pick the right vertical for a new file pack

When you receive a single pack of files for one use case (e.g., a set of docs, a code drop, or an API spec), you can auto-detect which existing vertical fits best (CODE, DOCUMENTS, STRUCTURED, SPREADSHEETS, MEDIA):

```bash
# Human-readable recommendation
python vertical_recommender.py recommend ./my_files

# JSON output (for automation)
python vertical_recommender.py recommend ./my_files --json > recommendation.json
```

The output includes:
- Recommended vertical type and confidence
- File counts by category and top extensions
- Suggested chunk size and overlap
- A ready-to-use comma-separated list of extensions for indexer filtering

Use the recommendation to choose your prefix (e.g., `cod`, `doc`, `str`) and run:

```bash
python main.py create_vertical --prefix <your-prefix>
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
python main.py run-indexer ix-pp-portal            # Process documents in main vertical
python main.py run-indexer ix-pp-portal-json       # Process OpenAPI chunks in JSON vertical
python main.py indexer-status ix-pp-portal-json    # Check JSON indexer progress
python main.py list-resources         # List search resources
python main.py setup-integrated-vectorization  # Create integrated vectorization (Copilot Studio ready) index
python main.py check-integrated-status         # Check integrated pipeline indexer status
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

### Integrated Vectorization (Copilot Studio Compatible)

The project also supports an "integrated vectorization" pipeline that aligns with the latest Azure AI Search guidance and is required for Microsoft Copilot Studio knowledge sources.

Command to create resources:

```bash
python main.py setup-integrated-vectorization
```

What it creates:

- Data Source: `ds-spofiles-integrated`
- Index: `idx-spofiles-integrated` (contains `content_vector` field, vectorizer attached)
- Skillset: `ss-spofiles-integrated` (split + embedding skill)
- Indexer: `ix-spofiles-integrated`

Then monitor:

```bash
python main.py check-integrated-status
```

Verification steps:

1. Check index statistics to confirm vectors stored (vector index size > 0)
2. Retrieve a document (optional) selecting only `content_vector` to ensure it's populated
3. Perform a vector text query:

Example REST query (PowerShell):

```powershell
$body = '{
   "vectorQueries": [
      { "kind": "text", "text": "company policies about vacation", "fields": "content_vector", "k": 5 }
   ],
   "select": "title,source_url"
}'
Invoke-RestMethod -Method Post -Uri "https://<YOUR_SEARCH>.search.windows.net/indexes/idx-spofiles-integrated/docs/search?api-version=2024-07-01" -Headers @{"api-key"="<ADMIN_KEY>";"Content-Type"="application/json"} -Body $body
```

If results return with meaningful titles and source URLs, integrated vectorization works.

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
python main.py check-integrated-status   # Integrated vectorization indexer
```

### Common Issues

1. **Storage Authentication Fails**:
   - Verify your app registration has `Storage Blob Data Contributor` role
   - Check that you're signed in with the correct account
   - Ensure storage account allows the authentication method
4. **Search Setup Failed**: Verify search service admin key and endpoint
5. **No Citations in Copilot**: Ensure `source_url` field mapping in Copilot Studio
6. **Empty Vector Field**:
   - Ensure you used `setup-integrated-vectorization` (adds skillset + outputFieldMappings)
   - Confirm skillset exists: check Azure Portal > Search Service > Skillsets
   - Check index stats: vector index size must be > 0
   - Verify embedding model deployment name matches `AZURE_OPENAI_EMBEDDING_MODEL`

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
## OpenAPI / Swagger JSON Vertical

To ingest OpenAPI chunks:
1. Upload your chunk `.txt` files to the JSON container (e.g. `pp-portal-navi-json`).
2. Run the JSON indexer:
   ```powershell
   python main.py run-indexer ix-pp-portal-json
   ```
3. Check status:
   ```powershell
   python main.py indexer-status ix-pp-portal-json
   ```
4. Use the Copilot Studio agent with index `idx-pp-portal-json` as a knowledge source.