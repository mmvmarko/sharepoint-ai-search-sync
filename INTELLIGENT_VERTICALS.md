# Intelligent Vertical Creator

## Overview

The **Intelligent Vertical Creator** automates the process of analyzing source files and creating optimized Azure AI Search verticals. Instead of manually determining chunking strategies and index configurations, this tool:

1. **Analyzes** your source files (types, sizes, content characteristics)
2. **Suggests** optimal vertical configurations (chunking, splitting, grouping)
3. **Creates** organized folder structures ready for integrated vectorization

## The Problem It Solves

**Before**: Every time you get a new set of documents with different characteristics, you need to:
- Manually inspect file types and sizes
- Guess optimal chunking parameters
- Decide whether to split into multiple indexes
- Configure each vertical manually
- Risk suboptimal search performance

**After**: The tool automatically:
- Analyzes all files in seconds
- Suggests optimal configurations based on file characteristics
- Creates ready-to-use vertical structures
- Provides clear next steps for deployment

## Architecture

```
Quick Recommendation Path (Default)
--------------------------------------------------------------
Source Files → Quick Analyze → Recommend Vertical → Blob Upload → Create Vertical → Indexer
     ↓              ↓                 ↓                ↓               ↓             ↓
  Single       Count by type     CODE/DOCS/        Azure Blob     main.py create_  Vectors in
  Pack         + confidence      STRUCTURED        container       vertical --prefix index

Advanced (Optional): Pre-organize Files Before Upload
--------------------------------------------------------------
Source Files → Deep Analysis → Suggestions → Folder Structure → Blob Upload → Create Vertical → Indexer
     ↓              ↓               ↓              ↓                ↓               ↓             ↓
  Mixed        File types      Optimized       Organized by     Azure Blob      main.py create_  Vectors in
  Content      & sizes         chunking        type/prefix       containers      vertical --prefix index
```

## Quick Recommendation Path (Default)

Use this when you have one pack of files for a single use case/index (e.g., documents, code drop, API spec). The tool recommends the best-fitting existing vertical (CODE, DOCUMENTS, STRUCTURED, SPREADSHEETS, MEDIA).

```bash
# Human-readable recommendation
python vertical_recommender.py recommend ./my_files

# JSON output (automation)
python vertical_recommender.py recommend ./my_files --json > recommendation.json
```

The output includes:
- Recommended vertical type and confidence
- File counts by category and top extensions
- Suggested chunk size and overlap
- A ready-to-use comma-separated list of extensions for indexer filtering

Next, create the vertical using your chosen prefix (for example: cod, doc, str):

```bash
python main.py create_vertical --prefix <your-prefix>
```

Upload your files to the appropriate blob container as usual (you can filter by the recommended extensions if desired), then monitor the indexer.

## Usage

### 1. Analyze Only (Dry Run)

Get suggestions without creating any files:

```bash
python intelligent_vertical_creator.py analyze ./source_directory
```

This will:
- Scan all files recursively
- Categorize by type (code, documents, structured, etc.)
- Calculate statistics
- Suggest optimal vertical configurations
- Display a detailed report

**Example Output:**
```
📊 INTELLIGENT VERTICAL ANALYSIS REPORT
================================================================================

📁 Total Files: 847
💾 Total Size: 156.3 MB

📋 Category Breakdown:
--------------------------------------------------------------------------------

  CODE
    Files: 523
    Total Size: 89.2 MB
    Avg Size: 174.6 KB
    Extensions: .css, .html, .js, .scss, .ts

  DOCUMENTS
    Files: 234
    Total Size: 45.1 MB
    Avg Size: 197.3 KB
    Extensions: .md, .pdf, .txt

  STRUCTURED
    Files: 90
    Total Size: 22.0 MB
    Avg Size: 250.4 KB
    Extensions: .json, .yaml

🎯 VERTICAL SUGGESTIONS:
================================================================================

1. Combined Vertical
   Prefix: all
   Category: combined
   Files: 847
   Size: 156.3 MB
   Extensions: .css, .html, .js, .json, .md, .pdf, .scss, .ts, .txt, .yaml
   Chunking: 2000 chars (overlap: 100)
   Container: verticals/combined
   All content types - 847 files

2. Code Vertical
   Prefix: cod
   Category: code
   Files: 523
   Size: 89.2 MB
   Extensions: .css, .html, .js, .scss, .ts
   Chunking: 3000 chars (overlap: 200)
   Container: verticals/code
   Source code files - 523 files, 89.2 MB

3. Documents Vertical
   Prefix: doc
   Category: documents
   Files: 234
   Size: 45.1 MB
   Extensions: .md, .pdf, .txt
   Chunking: 2000 chars (overlap: 100)
   Container: verticals/documents
   Office documents and text files - 234 files, 45.1 MB
```

### 2. Create Vertical Structure

Create organized folder structure based on analysis:

```bash
python intelligent_vertical_creator.py create-structure ./source_directory ./output_verticals
```

This will:
- Analyze the source directory
- Show the report
- Create folder structure in `./output_verticals/`
- Generate configuration files for each vertical
- Create file lists for organization

**Created Structure:**
```
output_verticals/
├── vertical_index.json          # Master index
├── verticals/
│   ├── combined/
│   │   ├── vertical_config.json # Vertical configuration
│   │   └── file_list.txt        # All matching files
│   ├── code/
│   │   ├── vertical_config.json
│   │   └── file_list.txt
│   └── documents/
│       ├── vertical_config.json
│       └── file_list.txt
```

**Select Specific Verticals:**
```bash
# Create only suggestions #2 and #3
python intelligent_vertical_creator.py create-structure ./source_directory ./output_verticals -s 2 -s 3
```

### 3. Interactive Mode

Best for first-time users:

```bash
python intelligent_vertical_creator.py interactive ./source_directory ./output_verticals
```

This will:
1. Analyze and show the report
2. Ask if you want to proceed
3. Let you select which verticals to create
4. Create the structure
5. Display next steps

**Interactive Flow:**
```
🔍 Analyzing directory...
[Shows analysis report]

❓ Create vertical structures based on these suggestions? [y/N]: y

📝 Select verticals to create:
   Enter numbers separated by spaces (e.g., '1 2 3')
   Or press Enter to create all

   Selection: 2 3

🏗️  Creating vertical structure...

✅ Done!
📂 Created 2 vertical(s) in: ./output_verticals
```

## Configuration Files

### vertical_config.json

Each vertical gets a configuration file:

```json
{
  "name": "Code Vertical",
  "prefix": "cod",
  "category": "code",
  "chunk_size": 3000,
  "overlap": 200,
  "file_extensions": [".css", ".html", ".js", ".scss", ".ts"],
  "indexed_extensions": ".css,.html,.js,.scss,.ts",
  "description": "Source code files - 523 files, 89.2 MB"
}
```

### vertical_index.json

Master index tracking all created verticals:

```json
{
  "created_at": "/path/to/project",
  "verticals": {
    "cod": {
      "directory": "./output_verticals/verticals/code",
      "config": "./output_verticals/verticals/code/vertical_config.json",
      "file_list": "./output_verticals/verticals/code/file_list.txt",
      "file_count": 523,
      "suggestion": { /* full suggestion details */ }
    }
  },
  "analysis_summary": {
    "total_files": 847,
    "total_size": 163850240,
    "categories": ["code", "documents", "structured"]
  }
}
```

## File Categories & Optimal Settings

The tool recognizes these categories with pre-tuned settings:

| Category | Extensions | Chunk Size | Overlap | Notes |
|----------|-----------|------------|---------|-------|
| **Code** | .py, .js, .ts, .java, .cpp, .cs, .go, .html, .css | 3000 | 200 | Larger chunks preserve context |
| **Documents** | .pdf, .docx, .pptx, .txt, .md, .rtf | 2000 | 100 | Standard office documents |
| **Structured** | .json, .xml, .yaml, .yml, .toml, .csv | 5000 | 0 | Keep structured data intact |
| **Spreadsheets** | .xlsx, .xls, .csv | 4000 | 50 | Balance between rows/context |
| **Media** | .png, .jpg, .gif, .mp4, .mp3 | N/A | N/A | Not text-indexed |

These settings are based on:
- **Average token limits** for embedding models (1536 dimensions)
- **Content coherence** (code functions, document paragraphs)
- **Search relevance** (overlap helps with boundary queries)
- **Azure AI Search limits** (maximum payload sizes)

## Complete Workflow

### Step 1: Analyze Your Files

```bash
python intelligent_vertical_creator.py analyze ./my_sharepoint_files --output analysis.json
```

Review the suggestions and decide on your approach.

### Step 2: Create Vertical Structure

```bash
python intelligent_vertical_creator.py create-structure ./my_sharepoint_files ./verticals_output -s 2 -s 3
```

### Step 3: Upload to Blob Storage

For each vertical, upload its files to a dedicated blob container:

```bash
# Example using Azure CLI
az storage blob upload-batch \
  --account-name mystorageaccount \
  --destination verticals-code \
  --source ./my_sharepoint_files \
  --pattern "*.js;*.ts;*.html" # Use extensions from vertical config
```

Or use the existing sync mechanism with different containers.

### Step 4: Create Azure AI Search Verticals

Use the generated configs to create each vertical:

```bash
# Read the vertical_config.json for each
cd ./verticals_output/verticals/code
cat vertical_config.json  # Note the prefix and extensions

# Create the vertical
python main.py create_vertical \
  --prefix cod \
  --container verticals-code
```

**Automated Script** (coming soon):
```bash
python deploy_verticals.py --config ./verticals_output/vertical_index.json
```

### Step 5: Monitor & Validate

```bash
# Check each indexer
python main.py indexer-status ix-cod
python main.py indexer-status ix-doc

# Validate vectors
python main.py check-integrated-status
```

## Advanced Features

### Custom Category Definitions

Edit `FILE_CATEGORIES` in `intelligent_vertical_creator.py` to add custom categories:

```python
FILE_CATEGORIES = {
    'legal': {
        'extensions': ['.pdf', '.docx'],
        'optimal_chunk_size': 4000,  # Longer legal paragraphs
        'overlap': 200,
        'description': 'Legal documents requiring larger context'
    },
    # ... existing categories
}
```

### Filtering by Size

You can modify the analysis to filter files by size thresholds:

```python
# In _analyze_file method
if stat.st_size > 100_000_000:  # Skip files > 100MB
    warnings.append(f"Skipping large file: {file_path}")
    return None
```

### Per-Project Verticals

If your source follows a project structure like `code_corpus_v2/`:

```bash
# Analyze each project separately
for project in ./code_corpus_v2/*; do
    python intelligent_vertical_creator.py analyze $project --output "${project}_analysis.json"
done

# Or create per-project verticals
python intelligent_vertical_creator.py create-structure ./code_corpus_v2/ATL__ATLANTIS__atlpp-main ./verticals_output/atlantis
```

## Integration with Existing System

### Option 1: Pre-Analysis for Manual Setup

Use analysis output to inform manual vertical creation:

```bash
python intelligent_vertical_creator.py analyze ./files --output suggestions.json
# Review suggestions.json
# Manually create verticals with optimized settings
python main.py create_vertical --prefix myprefix --container mycontainer
```

### Option 2: Automated Pipeline

Create a wrapper script that:
1. Runs analysis
2. Creates folder structures
3. Uploads to blob storage
4. Creates verticals via main.py
5. Monitors indexing

Example:
```bash
# auto_vertical_pipeline.sh
SOURCE=$1
PREFIX=$2

python intelligent_vertical_creator.py analyze $SOURCE
python intelligent_vertical_creator.py create-structure $SOURCE ./temp_verticals
# ... upload logic ...
python main.py create_vertical --prefix $PREFIX
python main.py indexer-status ix-$PREFIX
```

### Option 3: Direct Integration

Add analysis to `main.py` as a new command:

```python
@cli.command('smart-vertical')
@click.argument('source-dir')
@click.option('--prefix', required=True)
def smart_vertical(source_dir, prefix):
    """Analyze, suggest, and create vertical in one command."""
    from intelligent_vertical_creator import IntelligentVerticalCreator
    
    creator = IntelligentVerticalCreator()
    report = creator.analyze_directory(source_dir)
    creator.print_report(report)
    
    # Use first suggestion
    suggestion = report.vertical_suggestions[0]
    
    # Create vertical with optimal settings
    iv = AzureSearchIntegratedVectorization()
    iv.create_vertical(
        prefix,
        # Use suggestion settings...
    )
```

## Best Practices

### 1. Start with Analysis Only
Always run `analyze` first to understand your data before creating verticals.

### 2. Review Suggestions
The tool provides suggestions, but you know your use case best. Adjust as needed.

### 3. Test with Small Samples
Create test verticals with small file subsets before processing large datasets.

### 4. Use Descriptive Prefixes
Choose prefixes that match your organization: `legal`, `hr`, `eng`, `prod`, etc.

### 5. Monitor Resource Limits
Azure AI Search has limits on:
- Number of indexes per tier
- Storage per index
- Indexing throughput

Plan your verticals accordingly.

### 6. Document Your Decisions
Save analysis reports and keep notes on why you chose specific configurations.

## Troubleshooting

### "No files found"
- Check the directory path
- Verify file permissions
- Use `--recursive` flag if files are in subdirectories

### "Unknown category for many files"
- The tool doesn't recognize the extensions
- Add custom categories to `FILE_CATEGORIES`
- Or use the "combined" vertical

### "Vertical creation failed"
- Check Azure AI Search service limits
- Verify authentication
- Review the error message for specific issues

### "Files too large"
- Azure AI Search has document size limits (~32MB)
- Consider splitting large files before analysis
- Or exclude them with custom filtering

## Performance Considerations

- **Analysis Speed**: ~1000 files/second on SSD
- **Memory Usage**: ~100MB for 10,000 files
- **Storage**: Minimal (only creates configs, not file copies)

For very large datasets (>100k files), consider:
- Analyzing by subdirectory
- Sampling representative files
- Using parallel processing

## Future Enhancements

Planned features:
- [ ] Automatic blob upload integration
- [ ] One-command vertical deployment
- [ ] ML-based chunk size optimization
- [ ] Content similarity analysis for grouping
- [ ] Real-time index performance feedback
- [ ] Cost estimation per vertical
- [ ] Copilot Studio compatibility validation

## Examples

### Example 1: Code Repository

```bash
# Analyze a code repo
python intelligent_vertical_creator.py analyze ~/projects/my-app

# Output suggests:
# - Code vertical (3000 char chunks)
# - Docs vertical (2000 char chunks)
# - Config vertical (5000 char chunks, no overlap)

# Create structure
python intelligent_vertical_creator.py create-structure ~/projects/my-app ./verticals -s 1
```

### Example 2: SharePoint Document Library

```bash
# After syncing SharePoint to local
python main.py sync

# Analyze the local/blob files
python intelligent_vertical_creator.py analyze ./local_sharepoint_copy

# Create verticals based on document types
python intelligent_vertical_creator.py interactive ./local_sharepoint_copy ./verticals_output
```

### Example 3: Mixed Content Archive

```bash
# Large archive with unknown content
python intelligent_vertical_creator.py analyze /mnt/archive --output archive_analysis.json

# Review analysis
cat archive_analysis.json | jq '.vertical_suggestions'

# Create only the largest categories
python intelligent_vertical_creator.py create-structure /mnt/archive ./verticals -s 1 -s 2
```

## API Usage

You can also use the tool programmatically:

```python
from intelligent_vertical_creator import IntelligentVerticalCreator

creator = IntelligentVerticalCreator()

# Analyze
report = creator.analyze_directory('./my_files', recursive=True)

# Print report
creator.print_report(report)

# Access data
for suggestion in report.vertical_suggestions:
    print(f"Vertical: {suggestion.name}")
    print(f"Files: {suggestion.file_count}")
    print(f"Chunk: {suggestion.chunk_size}")

# Create structure
created = creator.create_vertical_structure(
    report,
    './output',
    selected_suggestions=[0, 1]  # First two suggestions
)

print(f"Created: {list(created.keys())}")
```

## Summary

The Intelligent Vertical Creator transforms vertical creation from a manual, error-prone process into an automated, optimized workflow:

**Before:**
- ❌ Manual file inspection
- ❌ Guessing chunking parameters
- ❌ Trial and error configuration
- ❌ Inconsistent results

**After:**
- ✅ Automatic analysis in seconds
- ✅ Data-driven suggestions
- ✅ Optimized configurations
- ✅ Repeatable process
- ✅ Clear deployment path

This tool ensures every vertical you create is optimized for its specific content type, leading to better search relevance, lower costs, and faster deployment.
