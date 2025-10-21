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
## 4. Command Glossary (current)

Command | Purpose | Typical When
--------|---------|-------------
`python main.py config_info` | Show configuration readiness | Before first run / troubleshooting
`python main.py setup_integrated_vectorization` | Create the standard integrated vectorization pipeline (default names) | One-off alternative to stable vertical
`python main.py create_vertical --prefix spo` | Create/update stable integrated vectorization vertical (ds/ss/idx/ix) | Initial setup for production/Copilot
`python main.py test_integrated --prefix demo` | Create disposable test vertical (random suffix) | Experiment safely
`python main.py delete_vertical --prefix spo` | Delete all vertical resources for prefix | Cleanup / rebuild
`python main.py list_resources` | List search service objects | Inspection
`python main.py run-indexer <indexerName>` | Run an indexer | Manual ingestion
`python main.py indexer-status <indexerName>` | Show indexer status/history | Monitoring
`python main.py full_setup` | End-to-end legacy flow (classic path) | Only if exploring old flow
`python main.py prepare-code --zip <file.zip> --project-name <Name> --project-code <Code> --out <dir>` | Build a text corpus from a project zip | Code vertical prep

> Recommended modern path: Use `create_vertical` (stable) or `setup_integrated_vectorization` (default names). Prefer the stable prefix approach (`spo`) for production.

---
## 5. End-to-End Initial Setup (Recommended Modern Path)

1) Verify config:
   ```bash
   python main.py config_info
   ```
2) Create stable integrated vertical:
   ```bash
   python main.py create_vertical --prefix spo
   ```
3) Monitor indexing:
   ```bash
   python main.py indexer-status ix-spo
   ```
4) Test semantic / vector query (REST example shown in README).
5) Add `idx-spo` as an Azure AI Search knowledge source in Copilot Studio.

Tip: If you used `setup_integrated_vectorization` instead, the default indexer name is `ix-spofiles-integrated`.

---
## 6. Re-ingesting Updated Content

When blobs change (e.g., new files uploaded or existing files replaced), re-run the indexer for your vertical so embeddings get regenerated:

- Safe re-run via vertical update (idempotent):
   ```bash
   python main.py create_vertical --prefix spo
   ```
   This PUTs resources and starts the indexer again.

- Or run the indexer directly:
   ```bash
   python main.py run-indexer ix-spo
   python main.py indexer-status ix-spo
   ```

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
Full reset (Search only) | Delete vertical(s) + recreate via steps in section 5

---
## 10. Troubleshooting Quick Reference

Problem | Likely Cause | Fix
--------|--------------|----
No documents in index | Indexer not run / wrong prefix | Run create_vertical again or check status
Vectors empty | Skillset missing / mapping issue (should be fixed now) | Recreate vertical; ensure OpenAI config
403/401 on embeddings | Wrong OpenAI endpoint or key | Check custom subdomain & key
Copilot rejects index | Non-integrated or Free tier service | Use integrated vertical on Basic+ tier
File updated but old answer | Indexer not re-run after blob change | Run `create_vertical --prefix spo` (or direct indexer run)
Imports unresolved warnings | Not packaged | (Optional) convert to package, or ignore—they are path-extended at runtime

---
## 11. Code Corpus Preparation (for CODE verticals)

If you have a zipped project and want to index its source as plain text, use `prepare-code`:

```powershell
python main.py prepare-code --zip "C:\path\to\project.zip" --project-name "MyProject" --project-code "ORG" --out code_corpus_myproject
```

What it does:
- Extracts text/code files by extension and writes normalized `.txt` files
- Supported highlights: .ts, .tsx, .js, .jsx, .mjs, .json, .md, .html, .css, .scss, .sass, .py, .java, .cs, .xml, .yml/.yaml, .gradle, .sh, .bat, .ps1, .sql
- Produces a summary at the end: Scanned / Collected / Skipped + “Skipped by type” (e.g., `.map`)
- Artifacts in the output folder:
   - `code_corpus_manifest.txt`
   - `file_map.txt`

Notes:
- Large source maps (e.g., `.mjs.map` / `.map`) are intentionally skipped to avoid noise and cost.
- After preparing the corpus, upload the generated `.txt` files to your target blob container for the CODE vertical.

---
## 12. JSON-Only Vertical (for OpenAPI or structured JSON)

You can create only the JSON vertical without the base one:

```powershell
python main.py create_vertical --prefix bo --json-only --json-container my-json-container
```

This creates resources with the `-json` suffix (e.g., `idx-bo-json`, `ix-bo-json`) and starts the indexer. If your prefix already ends with `-json` (e.g., `dev-bo-json`), names will become `*-json-json`—prefer a short base prefix (e.g., `bo`) when using `--json-only`.

Delete JSON-only verticals using the actual resource suffix, e.g.:

```powershell
# If created with --prefix bo --json-only
python main.py delete_vertical --prefix bo-json

# If you used a prefix already ending in -json (not recommended)
python main.py delete_vertical --prefix dev-bo-json-json
```

---
## 13. Best Practices
- Keep stable production vertical prefix short (`spo`, `docs`, `bo`, etc.)
- Periodically re-run `sync` before running indexer to minimize stale content.
- Avoid excessive disposable verticals to stay within service limits.
- Consider adding a schedule to the indexer if frequent updates are needed (can be added to indexer definition later).

---
## 14. Next Possible Enhancements (Not Yet Implemented)
Feature | Benefit
--------|--------
Scheduled indexer for vertical | Automates ingestion of new/changed blobs
Multi-chunk embeddings per document | Better recall for large files
Hybrid keyword + vector query helper | Faster relevance tuning
Vector stats CLI command | Quick confirmation of vector index size
Package restructuring | Cleaner imports + IDE support

Request any of these and they can be added.

---
## 15. Minimal Daily Ops Loop
```
python main.py create_vertical --prefix spo   # updates & runs indexer
python main.py indexer-status ix-spo
# Optional: semantic query / Copilot validation
```

---
**You now have a clean, repeatable workflow.** Use `create_vertical` (or direct indexer run) after content changes to re-embed. Reach out for any enhancements.
