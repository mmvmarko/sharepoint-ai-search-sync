# SharePoint to Azure AI Search Sync - Examples

This document provides examples of how to use the sync application.

## Getting SharePoint IDs

### Find Site ID

Use Microsoft Graph Explorer or make a request to:

```
GET https://graph.microsoft.com/v1.0/sites/{hostname}:{site-path}
```

Example for `https://contoso.sharepoint.com/sites/documents`:

```
GET https://graph.microsoft.com/v1.0/sites/contoso.sharepoint.com:/sites/documents:
```

Response includes the site ID in format: `contoso.sharepoint.com,{guid},{guid}`

### Find Drive ID

```
GET https://graph.microsoft.com/v1.0/sites/{site-id}/drives
```

Look for the drive with the document library you want to sync.

## Example Configuration

```env
# Azure AD Configuration
TENANT_ID=12345678-1234-1234-1234-123456789abc
CLIENT_ID=87654321-4321-4321-4321-ba9876543210

# SharePoint Configuration
SITE_ID=contoso.sharepoint.com,12345678-1234-1234-1234-123456789abc,87654321-4321-4321-4321-ba9876543210
DRIVE_ID=b!1234567890abcdef1234567890abcdef12345678_1234567890abcdef1234567890abcdef
FOLDER_PATH=Shared Documents/Policies

# Azure Storage Configuration
AZ_STORAGE_URL=https://mystrg.blob.core.windows.net
AZ_CONTAINER=spofiles
AZ_SAS=?sv=2022-11-02&ss=b&srt=co&sp=rwdl&se=2024-12-31T23:59:59Z&st=2024-01-01T00:00:00Z&spr=https&sig=abcd1234...

# Azure AI Search Configuration
SEARCH_SERVICE_NAME=my-search-service
SEARCH_API_KEY=1234567890ABCDEF1234567890ABCDEF
SEARCH_ENDPOINT=https://my-search-service.search.windows.net
```

## Usage Examples

### First Time Setup

```bash
# 1. Check your configuration
python main.py config-info

# 2. Run complete setup (easiest option)
python main.py full-setup
```

### Individual Steps

```bash
# Set up Azure AI Search pipeline
python main.py setup-search

# Sync SharePoint content to blob storage  
python main.py sync

# Run indexer to process documents
python main.py run-indexer

# Check indexer progress
python main.py indexer-status
```

### With Vector Search (requires Azure OpenAI)

```bash
# Set up search with embeddings
python main.py setup-search --embeddings

# This requires Azure OpenAI configuration in .env:
# AZURE_OPENAI_ENDPOINT=https://my-openai.openai.azure.com
# AZURE_OPENAI_API_KEY=abc123...
# AZURE_OPENAI_EMBEDDING_MODEL=text-embedding-ada-002
```

### Ongoing Operations

```bash
# Run incremental sync (only changed files)
python main.py sync

# Monitor indexer status
python main.py indexer-status

# List all search resources
python main.py list-resources
```

## Authentication Flow

When you run sync for the first time:

1. You'll see a message like: "To sign in, use a web browser to open the page https://microsoft.com/devicelogin and enter the code ABC123DEF to authenticate."
2. Open the URL in your browser
3. Enter the provided code
4. Sign in with your Microsoft account that has access to SharePoint
5. Grant permissions to the application
6. Return to the terminal - sync will continue automatically

## Troubleshooting Examples

### Check Configuration Issues

```bash
python main.py config-info
```

Output example:
```
=== Configuration Status ===
SharePoint: ✓
Azure Storage: ✓
Azure AI Search: ✗
  Missing: SEARCH_SERVICE_NAME, SEARCH_API_KEY, or SEARCH_ENDPOINT
Azure OpenAI (optional): ✗
  Vector search disabled - missing AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY
```

### Debug Sync Issues

```bash
# Enable debug logging
python main.py --debug sync
```

### Check Indexer Problems

```bash
python main.py indexer-status
```

Example output:
```
=== Indexer Status: ix-spofiles ===
Status: running

Last Execution:
  Status: inProgress
  Start Time: 2024-01-15T10:30:00Z
  End Time: Unknown
  Items Processed: 15
  Items Failed: 0

Execution History (3 runs):
  1. 2024-01-15T10:30:00Z - inProgress (15 items)
  2. 2024-01-15T09:00:00Z - success (12 items)
  3. 2024-01-15T08:30:00Z - success (10 items)
```

## File Organization in Blob Storage

Files are stored preserving the SharePoint folder structure:

```
Container: spofiles
├── Shared Documents/
│   ├── Policies/
│   │   ├── HR Policy.pdf
│   │   ├── HR Policy.pdf.json (sidecar)
│   │   ├── Security Guidelines.docx
│   │   └── Security Guidelines.docx.json (sidecar)
│   └── Templates/
│       ├── Project Template.pptx
│       └── Project Template.pptx.json (sidecar)
```

Each file gets:
- The original document
- A `.json` sidecar with metadata including the SharePoint URL

## Copilot Studio Setup

1. In Copilot Studio, go to your agent
2. Click "Add knowledge" → "Azure AI Search"
3. Enter your search service details:
   - Service name: `my-search-service`
   - Index name: `idx-spofiles`
   - API key: `your-search-admin-key`
4. **Important**: In field mapping, map `source_url` as the URL field
5. Test with a question about your documents
6. Verify that answers include clickable SharePoint links

## Advanced Usage

### Custom Index Names

```bash
# Use custom names for search resources
python main.py setup-search
# Then manually modify the created resources or use the search_manager.py script
```

### Scheduled Syncing

Set up a scheduled task (Windows) or cron job (Linux) to run:

```bash
python main.py sync
```

The delta API ensures only changed files are processed.

### Large Document Libraries

For libraries with thousands of documents:
- Monitor indexer execution time
- Consider filtering file types in the indexer configuration
- Use Standard or higher tier for Azure AI Search
- Enable storage analytics to monitor blob operations