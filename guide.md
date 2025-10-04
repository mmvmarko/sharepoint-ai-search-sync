# SharePoint → Azure AI Search Sync & Integrated Vectorization Guide

This guide explains what the application does, the commands it offers, and the correct workflows—especially how to propagate SharePoint file changes into the Azure AI Search vector index (Copilot Studio–ready).

---
## 1. What the Application Does

| Capability | Description |
|------------|-------------|
| SharePoint Sync | Uses Microsoft Graph (delta API) to incrementally pull files from a SharePoint document library. |
| Blob Storage Upload | Stores file binaries + metadata + sidecar JSON into an Azure Blob container. |
| Vector Index Creation | Creates Azure AI Search index with integrated vectorization (vector field + vectorizer). |
| Skillset | Splits content (basic page splitting) and generates embeddings via Azure OpenAI. |
| Indexer | Pulls from blob storage, runs skillset, stores text + vectors in the search index. |
| Quick Test Resources | Disposable, timestamped vertical (ds/idx/ss/ix) for experimentation. |
| Stable Vertical | Re-usable, prefix-based set (e.g. `spo`) safe to point Copilot Studio at. |
| Cleanup | Deletes all resources for a given prefix. |

---
## 2. Core Concepts

Term | Meaning
-----|--------
Vertical | A consistent set of Search resources: Data Source, Skillset, Index, Indexer.
Integrated Vectorization | Azure AI Search auto-generates embeddings at index time and query time (vectorizer + embedding skill).
Delta Sync | Captures only changes in SharePoint after the first full run (uses `delta_state.json`).

---
## 3. Environment Variables (Summary)
You must configure these in `.env` (see existing README for full template):
- TENANT_ID, CLIENT_ID, (CLIENT_SECRET optional if using app secret flow)
- SITE_ID, DRIVE_ID, FOLDER_PATH
- AZ_STORAGE_URL, AZ_CONTAINER
- SEARCH_SERVICE_NAME, SEARCH_API_KEY, SEARCH_ENDPOINT
- AZURE_OPENAI_ENDPOINT (custom subdomain), AZURE_OPENAI_API_KEY, AZURE_OPENAI_EMBEDDING_MODEL

---
## 4. Command Glossary

Command | Purpose | Typical When
--------|---------|-------------
`python main.py config-info` | Show configuration readiness | Before first run / troubleshooting
`python main.py sync` | Sync (initial + incremental) SharePoint → Blob | New or changed files in SharePoint
`python main.py setup-search` | (Legacy) Creates classic pipeline with embeddings (non-integrated vectorizer) | Only if exploring old flow
`python main.py setup-integrated-vectorization` | Create the standard integrated vectorization pipeline (default names) | One-off alternative to stable vertical
`python main.py create_vertical --prefix spo` | Create/update stable integrated vectorization vertical (ds/ss/idx/ix) | Initial setup for production/Copilot
`python main.py check-integrated-status` | Check status of the integrated indexer (default names) | After setup-integrated-vectorization
`python main.py test_integrated --prefix demo` | Create disposable test vertical (random suffix) | Experiment safely
`python main.py delete_vertical --prefix spo` | Delete all vertical resources for prefix | Cleanup / rebuild
`python main.py list-resources` | List search service objects (classic path) | Inspection
`python main.py run-indexer` | Run legacy indexer (classic pipeline) | Only with setup-search path
`python main.py indexer-status` | Status of legacy indexer | Legacy path only
`python main.py full-setup` | Legacy end-to-end (classic index) | Not needed for integrated vertical

> Recommended modern path: Use `create_vertical` (stable) or `setup-integrated-vectorization` (default names). Prefer the stable prefix approach (`spo`) for production.

---
## 5. End-to-End Initial Setup (Recommended Modern Path)

1. Verify config:
   ```bash
   python main.py config-info
   ```
2. Sync SharePoint content to Blob:
   ```bash
   python main.py sync
   ```
3. Create stable integrated vertical:
   ```bash
   python main.py create_vertical --prefix spo
   ```
4. Monitor indexing:
   ```bash
   python main.py check-integrated-status
   ```
5. Test semantic / vector query (REST example shown in main README).
6. Add `idx-spo` as an Azure AI Search knowledge source in Copilot Studio.

---
## 6. Propagating a File Change from SharePoint to the Index

Scenario: A file in SharePoint was updated and you need the new content + embeddings reflected in the vector index.

Workflow:
1. Run incremental sync (delta picks up change):
   ```bash
   python main.py sync
   ```
2. Re-run (or wait on scheduled) indexer. For the stable vertical created via `create_vertical`, the indexer was run once at creation. If you need to run it again manually:
   - (Option A) Re-run vertical creation (safe idempotent update + run):
     ```bash
     python main.py create_vertical --prefix spo
     ```
     This updates definitions (PUT semantics) and starts the indexer again.
   - (Option B) Issue direct REST call to run indexer `ix-spo`:
     ```bash
     # PowerShell example
     Invoke-RestMethod -Method Post `
       -Uri "https://<SEARCH_SERVICE>.search.windows.net/indexers/ix-spo/run?api-version=2024-07-01" `
       -Headers @{"api-key"="<ADMIN_KEY>"}
     ```
3. Monitor status:
   ```bash
   python main.py check-integrated-status
   ```
4. (Optional) Validate updated content via a text+vector query.

Why you must re-run the indexer: Sync only updates blobs. The indexer must ingest those updated blobs and regenerate the embedding (skillset). If you skip re-running, the index will still have the old vector.

---
## 7. Updating the Embedding Model or Dimensions

If you change `AZURE_OPENAI_EMBEDDING_MODEL` or want different dimensions:
1. Delete or recreate the vertical:
   ```bash
   python main.py delete_vertical --prefix spo
   ```
2. Recreate:
   ```bash
   python main.py create_vertical --prefix spo
   ```
3. Re-sync if necessary (if blobs already there, just recreate vertical; indexer will extract again).

---
## 8. Disposable Test Workflow

1. Create a test vertical:
   ```bash
   python main.py test_integrated --prefix experiment
   ```
2. Run tests / queries.
3. Delete when finished:
   ```bash
   python main.py delete_vertical --prefix experiment
   ```

---
## 9. Cleanup & Rebuild

Action | Command
-------|--------
Delete stable vertical | `python main.py delete_vertical --prefix spo`
Delete a test vertical | `python main.py delete_vertical --prefix demo` (or chosen prefix)
Full reset (Search only) | Delete all verticals + recreate via steps in section 5
Full reset (including delta) | Remove `delta_state.json` + rerun `python main.py sync`

---
## 10. Troubleshooting Quick Reference

Problem | Likely Cause | Fix
--------|--------------|----
No documents in index | Indexer not run / wrong prefix | Run create_vertical again or check status
Vectors empty | Skillset missing / mapping issue (should be fixed now) | Recreate vertical; ensure OpenAI config
403/401 on embeddings | Wrong OpenAI endpoint or key | Check custom subdomain & key
Copilot rejects index | Non-integrated or Free tier service | Use integrated vertical on Basic+ tier
File updated but old answer | Indexer not re-run post sync | Run `create_vertical --prefix spo` (or direct indexer run)
Imports unresolved warnings | Not packaged | (Optional) convert to package, or ignore—they are path-extended at runtime

---
## 11. Best Practices
- Keep stable production vertical prefix short (`spo`, `docs`, etc.)
- Periodically re-run `sync` before running indexer to minimize stale content.
- Avoid excessive disposable verticals to stay within service limits.
- Consider adding a schedule to the indexer if frequent updates are needed (can be added to indexer definition later).

---
## 12. Next Possible Enhancements (Not Yet Implemented)
Feature | Benefit
--------|--------
Scheduled indexer for vertical | Automates ingestion of new/changed blobs
Multi-chunk embeddings per document | Better recall for large files
Hybrid keyword + vector query helper | Faster relevance tuning
Vector stats CLI command | Quick confirmation of vector index size
Package restructuring | Cleaner imports + IDE support

Request any of these and they can be added.

---
## 13. Minimal Daily Ops Loop
```
python main.py sync
python main.py create_vertical --prefix spo   # (or REST run indexer)
python main.py check-integrated-status
# Optional: semantic query / Copilot validation
```

---
**You now have a clean, repeatable workflow.** Use `sync` for content changes and `create_vertical` (or direct indexer run) to re-embed. Reach out for any enhancements.
