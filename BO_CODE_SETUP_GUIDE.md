# BO Code Processing & Azure AI Search Integration Guide

## Overview

This guide walks you through processing the `BO_Code.zip` (16 API modules with OpenAPI specs + generated code) and creating integrated vectorization indexes in Azure AI Search.

---

## 📁 What's in BO_Code.zip?

**16 API Modules**, each containing:
- `swagger.json` - OpenAPI/Swagger specification with metadata
- `ngx-<module>/` - Generated TypeScript client code (~100-1100 files per module)
- `scrapper.log` - Build logs (skipped during processing)

**Modules:**
- CORE (BO Portal API) - 1,109 code files
- BANKEXTENSIONS - 51 files
- CAMPAIGN - 154 files
- CMS - 137 files
- CRYPTOPAYMENTS - 31 files
- GAMIFICATION - 145 files
- INHOUSEBANK - 39 files
- JACKPOT - 106 files
- MAN - 66 files
- REFERRALS - 67 files
- REWARDGAME - 73 files
- SBR - 76 files
- SC - 100 files
- SPL - 34 files
- STB - 76 files
- TOURNAMENTS - 162 files

**Total:** 2,426 code files + 16 OpenAPI specs

---

## 🎯 Processing Strategy

We create **TWO separate verticals** (search indexes):

### 1. **OpenAPI/Swagger Vertical** (Small, structured)
- **Content:** 16 enriched JSON files with API documentation
- **Purpose:** Semantic search over API endpoints, schemas, operations
- **Size:** ~16 documents
- **Use case:** "What endpoints handle player bonuses?" "How does the Campaign API work?"

### 2. **Code Corpus Vertical** (Large, detailed)
- **Content:** 2,426 normalized TypeScript files
- **Purpose:** Deep code search, implementation details, type definitions
- **Size:** ~2,426 documents
- **Use case:** "Show me the BonusService implementation" "Find interfaces related to tournaments"

---

## 📋 Step-by-Step Process

### **Step 1: Prepare the Files**

Run the new `prepare-bo-code` command:

```powershell
python main.py prepare-bo-code --zip BO_Code.zip --out bo_prepared
```

**Output structure:**
```
bo_prepared/
├── swagger/
│   ├── swagger_CORE.json          (enriched with x-module, x-folder metadata)
│   ├── swagger_CAMPAIGN.json
│   ├── swagger_CMS.json
│   ├── ... (16 total)
│   └── _manifest.txt
├── code/
│   ├── CORE__<path>__<hash>.txt   (normalized with headers)
│   ├── CAMPAIGN__<path>__<hash>.txt
│   ├── ... (2,426 total)
│   └── _manifest.txt
└── SUMMARY.txt                     (full processing report)
```

**What happens:**
- ✅ Extracts all 16 modules
- ✅ Enriches swagger.json files with `x-module`, `x-folder`, `x-source-file` metadata
- ✅ Converts code files to `.txt` with contextual headers
- ✅ Skips `.map` files (source maps) and `.log` files
- ✅ Includes `.d.ts`, `.ts`, `.tsx`, `.js`, `.json`, `.md` files

---

### **Step 2: Upload to Azure Blob Storage**

You need **TWO blob containers** (or use the same container with folder prefixes):

#### Option A: Separate Containers (Recommended)

```powershell
# Upload OpenAPI files
az storage blob upload-batch `
  --account-name <your-storage-account> `
  --destination bo-swagger `
  --source "bo_prepared\swagger" `
  --auth-mode login

# Upload code files
az storage blob upload-batch `
  --account-name <your-storage-account> `
  --destination bo-code `
  --source "bo_prepared\code" `
  --auth-mode login
```

#### Option B: Single Container with Folders

```powershell
az storage blob upload-batch `
  --account-name <your-storage-account> `
  --destination bo-content `
  --source "bo_prepared\swagger" `
  --destination-path swagger `
  --auth-mode login

az storage blob upload-batch `
  --account-name <your-storage-account> `
  --destination bo-content `
  --source "bo_prepared\code" `
  --destination-path code `
  --auth-mode login
```

---

### **Step 3: Create OpenAPI Vertical (JSON-only)**

This vertical indexes the 16 swagger JSON files with semantic vectorization.

```powershell
python main.py create_vertical --prefix bo-swagger --json-only --json-container bo-swagger
```

**What it creates:**
- `ds-bo-swagger-json` - Data source pointing to blob container
- `ss-bo-swagger-json` - Skillset with JSON splitting + OpenAI embeddings
- `idx-bo-swagger-json` - Index with vector field for semantic search
- `ix-bo-swagger-json` - Indexer to process files

**Monitor indexing:**
```powershell
python main.py indexer-status ix-bo-swagger-json
```

**Test query (REST API):**
```powershell
$headers = @{
    "Content-Type" = "application/json"
    "api-key" = "<your-search-api-key>"
}

$body = @{
    "search" = "player bonus endpoints"
    "vectorQueries" = @(
        @{
            "kind" = "text"
            "text" = "player bonus endpoints"
            "fields" = "contentVector"
            "k" = 5
        }
    )
    "select" = "title,content"
    "top" = 5
} | ConvertTo-Json -Depth 10

Invoke-RestMethod -Uri "https://<search-service>.search.windows.net/indexes/idx-bo-swagger-json/docs/search?api-version=2024-07-01" `
    -Method POST `
    -Headers $headers `
    -Body $body
```

---

### **Step 4: Create Code Vertical**

This vertical indexes the 2,426 code files.

```powershell
python main.py create_vertical --prefix bo-code
```

**Note:** If your code files are in a different container than your `.env` default, update settings:
- Edit `.env` → `AZ_CONTAINER=bo-code` (or your container name)
- Or pass container explicitly when creating vertical (requires code modification)

**What it creates:**
- `ds-bo-code` - Data source pointing to code blob container
- `ss-bo-code` - Skillset with text splitting + OpenAI embeddings
- `idx-bo-code` - Index with vector field
- `ix-bo-code` - Indexer

**Monitor indexing:**
```powershell
python main.py indexer-status ix-bo-code
```

---

### **Step 5: Verify & Test**

#### Check index document counts:
```powershell
# OpenAPI vertical
python main.py list_resources

# Or via REST:
Invoke-RestMethod -Uri "https://<search-service>.search.windows.net/indexes/idx-bo-swagger-json/stats?api-version=2024-07-01" `
    -Headers @{"api-key"="<key>"}

Invoke-RestMethod -Uri "https://<search-service>.search.windows.net/indexes/idx-bo-code/stats?api-version=2024-07-01" `
    -Headers @{"api-key"="<key>"}
```

**Expected results:**
- `idx-bo-swagger-json`: ~16 documents
- `idx-bo-code`: ~2,426 documents

#### Test semantic queries:

**OpenAPI queries:**
- "Show me campaign API endpoints"
- "What are the player management operations?"
- "Bonus configuration schema"

**Code queries:**
- "BonusService implementation"
- "Tournament interfaces and models"
- "Payment processing functions"

---

### **Step 6: Connect to Copilot Studio**

1. In Copilot Studio, go to **Knowledge sources**
2. Click **Add knowledge** → **Azure AI Search**
3. Add connection details:
   - **Index 1:** `idx-bo-swagger-json` (OpenAPI docs)
   - **Index 2:** `idx-bo-code` (code corpus)
4. Enable both for your copilot
5. Test queries through the chat interface

---

## 🔄 Updating Content

### When you get a new BO_Code.zip:

```powershell
# 1. Prepare new files
python main.py prepare-bo-code --zip BO_Code_v2.zip --out bo_prepared_v2

# 2. Upload to blob (overwrites existing)
az storage blob upload-batch --account-name <account> --destination bo-swagger --source "bo_prepared_v2\swagger" --overwrite --auth-mode login
az storage blob upload-batch --account-name <account> --destination bo-code --source "bo_prepared_v2\code" --overwrite --auth-mode login

# 3. Re-run indexers (picks up changes automatically)
python main.py run-indexer ix-bo-swagger-json
python main.py run-indexer ix-bo-code

# 4. Monitor completion
python main.py indexer-status ix-bo-swagger-json
python main.py indexer-status ix-bo-code
```

---

## 🛠️ Troubleshooting

### Problem: "No documents indexed"
**Solution:** Check indexer status for errors
```powershell
python main.py indexer-status ix-bo-swagger-json
```

### Problem: "Vector field is empty"
**Solution:** 
- Verify `AZURE_OPENAI_ENDPOINT` uses custom subdomain format: `https://<resource-name>.openai.azure.com`
- Check `AZURE_OPENAI_API_KEY` is correct
- Recreate vertical if settings changed

### Problem: "Indexer fails with 403"
**Solution:** Check blob container permissions - ensure search service managed identity has "Storage Blob Data Reader" role

### Problem: "Too many documents / quota exceeded"
**Solution:** 
- Code vertical is large (2,426 files) - consider filtering by module
- Basic tier: 15 GB limit
- Standard tier: 200 GB limit

### Problem: "Copilot can't find my index"
**Solution:**
- Ensure you're on Basic tier or higher (Free tier not supported)
- Verify integrated vectorization is enabled (it is with our scripts)
- Check index shows "vectorizers" in definition

---

## 📊 Resource Naming

| Resource Type | OpenAPI Vertical | Code Vertical |
|--------------|------------------|---------------|
| Data Source | `ds-bo-swagger-json` | `ds-bo-code` |
| Skillset | `ss-bo-swagger-json` | `ss-bo-code` |
| Index | `idx-bo-swagger-json` | `idx-bo-code` |
| Indexer | `ix-bo-swagger-json` | `ix-bo-code` |

---

## 🎨 Advanced: Module-Specific Indexes

If you want separate indexes per module (e.g., only CAMPAIGN API):

1. **Filter during preparation** (would require script modification)
2. **Or upload specific files:**
   ```powershell
   # Upload only CAMPAIGN files
   Get-ChildItem "bo_prepared\code\CAMPAIGN__*" | ForEach-Object {
       az storage blob upload --account-name <account> --container bo-code-campaign --file $_.FullName --name $_.Name
   }
   ```
3. **Create vertical:**
   ```powershell
   # Update .env or modify create_vertical to use bo-code-campaign container
   python main.py create_vertical --prefix campaign
   ```

---

## 📈 Performance Tips

1. **Indexer schedule:** Add automatic refresh
   ```powershell
   # Modify indexer to run every 6 hours (manual via Azure Portal or REST API)
   ```

2. **Chunk sizing:** Current default is good for code, but can be tuned in skillset

3. **Embedding dimensions:** Using `text-embedding-ada-002` (1536 dims) or `text-embedding-3-small` (configurable)

4. **Query optimization:** Use hybrid search (keyword + vector) for best results

---

## 🧹 Cleanup

To delete verticals:

```powershell
# Delete OpenAPI vertical
python main.py delete_vertical --prefix bo-swagger-json

# Delete code vertical
python main.py delete_vertical --prefix bo-code
```

To delete blob containers:
```powershell
az storage container delete --name bo-swagger --account-name <account> --auth-mode login
az storage container delete --name bo-code --account-name <account> --auth-mode login
```

---

## 🚀 Quick Reference Commands

```powershell
# Initial setup
python main.py prepare-bo-code --zip BO_Code.zip --out bo_prepared
az storage blob upload-batch --account-name <account> --destination bo-swagger --source "bo_prepared\swagger" --auth-mode login
az storage blob upload-batch --account-name <account> --destination bo-code --source "bo_prepared\code" --auth-mode login
python main.py create_vertical --prefix bo-swagger --json-only --json-container bo-swagger
python main.py create_vertical --prefix bo-code

# Monitoring
python main.py indexer-status ix-bo-swagger-json
python main.py indexer-status ix-bo-code
python main.py list_resources

# Updates
python main.py run-indexer ix-bo-swagger-json
python main.py run-indexer ix-bo-code

# Cleanup
python main.py delete_vertical --prefix bo-swagger-json
python main.py delete_vertical --prefix bo-code
```

---

## ✅ Success Criteria

- [ ] Files prepared successfully (16 swagger + 2,426 code files)
- [ ] Blobs uploaded to Azure Storage
- [ ] OpenAPI vertical created and indexed (~16 docs)
- [ ] Code vertical created and indexed (~2,426 docs)
- [ ] Semantic queries return relevant results
- [ ] Copilot Studio connected to both indexes
- [ ] Copilot answers questions using BO API knowledge

---

**You're all set!** 🎉 Follow the steps in order, and you'll have a fully functional multi-vertical search solution for your BO APIs.
