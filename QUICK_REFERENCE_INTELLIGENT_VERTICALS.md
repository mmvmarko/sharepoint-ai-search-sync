# Quick Reference: Intelligent Vertical Creator

## TL;DR

**Problem**: Different source files need different chunking strategies, but manually configuring each vertical is time-consuming and error-prone.

**Solution**: Automatic file analysis → Intelligent suggestions → Ready-to-deploy verticals

## Quick Commands

```bash
# 1. Analyze files (dry run)
python intelligent_vertical_creator.py analyze ./my_files

# 2. Create vertical structure
python intelligent_vertical_creator.py create-structure ./my_files ./output

# 3. Interactive mode (recommended for first time)
python intelligent_vertical_creator.py interactive ./my_files ./output

# 4. Select specific verticals
python intelligent_vertical_creator.py create-structure ./my_files ./output -s 1 -s 3

# 5. Run examples
python example_intelligent_vertical_workflow.py
```

## Decision Tree

```
Do you know your file types and optimal chunking?
│
├─ YES → Use existing main.py create_vertical
│         python main.py create_vertical --prefix myprefix
│
└─ NO → Use Intelligent Vertical Creator
    │
    ├─ First time?
    │  └─ Use interactive mode:
    │     python intelligent_vertical_creator.py interactive ./files ./output
    │
    ├─ Want to review before creating?
    │  └─ Analyze first:
    │     python intelligent_vertical_creator.py analyze ./files
    │     Then create:
    │     python intelligent_vertical_creator.py create-structure ./files ./output
    │
    └─ Automating in a script?
       └─ Use programmatically:
          from intelligent_vertical_creator import IntelligentVerticalCreator
          creator = IntelligentVerticalCreator()
          report = creator.analyze_directory('./files')
```

## File Categories Cheat Sheet

| Category | When to Use | Chunk Size | Overlap |
|----------|-------------|------------|---------|
| **code** | .py, .js, .ts, .java, .cpp | 3000 | 200 |
| **documents** | .pdf, .docx, .txt, .md | 2000 | 100 |
| **structured** | .json, .xml, .yaml | 5000 | 0 |
| **spreadsheets** | .xlsx, .csv | 4000 | 50 |

## Typical Workflows

### Workflow 1: New Document Set

```bash
# Step 1: Analyze
python intelligent_vertical_creator.py analyze ./new_documents --output analysis.json

# Step 2: Review suggestions in analysis.json
cat analysis.json | jq '.vertical_suggestions'

# Step 3: Create structure for selected verticals
python intelligent_vertical_creator.py create-structure ./new_documents ./verticals -s 1 -s 2

# Step 4: Upload to blob (your method)
# ... upload files to blob containers ...

# Step 5: Create Azure AI Search verticals
cd ./verticals/verticals/documents
cat vertical_config.json  # Check prefix and settings
python main.py create_vertical --prefix doc --container verticals-documents

# Step 6: Monitor
python main.py indexer-status ix-doc
```

### Workflow 2: Recurring Updates

```bash
# Analyze new batch
python intelligent_vertical_creator.py analyze ./new_batch

# Use existing vertical structure (same categories)
# Just upload new files and re-run indexer
python main.py sync
python main.py create_vertical --prefix existing_prefix
```

### Workflow 3: Per-Project Verticals

```bash
# Analyze each project
for project in ./projects/*; do
    python intelligent_vertical_creator.py analyze $project --output "${project}_analysis.json"
done

# Create verticals for each
for project in ./projects/*; do
    prefix=$(basename $project | tr '[:upper:]' '[:lower:]' | cut -c1-5)
    python intelligent_vertical_creator.py create-structure $project ./verticals_$prefix
    # ... then create Azure vertical with that prefix
done
```

## Output Files Explained

### vertical_config.json
```json
{
  "name": "Code Vertical",           // Human-readable name
  "prefix": "cod",                    // Use in create_vertical --prefix
  "chunk_size": 3000,                 // Optimal for this file type
  "overlap": 200,                     // Context overlap
  "file_extensions": [".py", ".js"],  // Files in this vertical
  "indexed_extensions": ".py,.js"     // Ready for indexer config
}
```

### vertical_index.json
Master inventory of all created verticals. Use for automation.

### file_list.txt
All files that match this vertical's criteria. Use for upload scripts.

## Integration Points

### With Existing main.py

```bash
# After creating structure with intelligent_vertical_creator:
cd output/verticals/code

# Read the config
PREFIX=$(jq -r '.prefix' vertical_config.json)
EXTENSIONS=$(jq -r '.indexed_extensions' vertical_config.json)

# Create the vertical
python main.py create_vertical --prefix $PREFIX
```

### With Azure Storage Upload

```bash
# Read extensions from config
EXTENSIONS=$(jq -r '.file_extensions | join(";*")' vertical_config.json)

# Upload matching files
az storage blob upload-batch \
  --account-name $STORAGE \
  --destination $CONTAINER \
  --source ./files \
  --pattern "*$EXTENSIONS"
```

### With CI/CD Pipeline

```yaml
# .github/workflows/create-verticals.yml
- name: Analyze Files
  run: |
    python intelligent_vertical_creator.py analyze ./docs --output analysis.json

- name: Create Verticals
  run: |
    python intelligent_vertical_creator.py create-structure ./docs ./verticals

- name: Deploy to Azure
  run: |
    for config in ./verticals/**/vertical_config.json; do
      prefix=$(jq -r '.prefix' $config)
      python main.py create_vertical --prefix $prefix
    done
```

## Common Patterns

### Pattern: Split by Size

```python
# In your script
from intelligent_vertical_creator import IntelligentVerticalCreator

creator = IntelligentVerticalCreator()
report = creator.analyze_directory('./files')

# Separate large and small files
large_files = [f for f in report.file_analyses if f.size > 10_000_000]
small_files = [f for f in report.file_analyses if f.size <= 10_000_000]

# Create separate verticals for each
# ... custom logic ...
```

### Pattern: By Date/Folder

```bash
# Create vertical per year
for year in 2022 2023 2024; do
    python intelligent_vertical_creator.py analyze ./archive/$year --output ${year}_analysis.json
    python intelligent_vertical_creator.py create-structure ./archive/$year ./verticals_$year
done
```

### Pattern: By Content Type

```bash
# Already handled by categories, but you can further refine:
python intelligent_vertical_creator.py analyze ./files
# Then manually create verticals based on extensions:
# legal-docs: .pdf + .docx from legal folder
# tech-specs: .md + .pdf from specs folder
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No vertical suggestions" | Files may not match known categories. Add custom categories. |
| "Analysis takes too long" | Use `--no-recursive` or analyze subdirectories separately. |
| "Wrong category detected" | Extensions may overlap. Manually specify in create_vertical. |
| "Chunk size seems wrong" | Suggested values are defaults. Override when creating vertical. |

## Tips

1. **Always analyze first** - Understand your data before committing
2. **Save analysis.json** - Useful for comparing different file sets
3. **Start small** - Test with one vertical before bulk creation
4. **Use prefixes consistently** - Makes management easier
5. **Document decisions** - Keep notes on why you chose specific configurations
6. **Monitor performance** - Adjust chunk sizes based on search quality

## Next Steps After Creating Verticals

1. ✅ Files analyzed
2. ✅ Structure created
3. 📤 **Upload to blob storage**
4. 🔍 **Create Azure AI Search vertical**
5. ⚙️ **Monitor indexing**
6. 🧪 **Test queries**
7. 🤖 **Connect to Copilot Studio**

## Resources

- Full Documentation: `INTELLIGENT_VERTICALS.md`
- Examples: `python example_intelligent_vertical_workflow.py`
- Main Guide: `guide.md`
- API Reference: See docstrings in `intelligent_vertical_creator.py`

## One-Liners for Common Tasks

```bash
# Quick analysis
python intelligent_vertical_creator.py analyze .

# Create everything
python intelligent_vertical_creator.py interactive . ./output

# Just code files
python intelligent_vertical_creator.py analyze ./src -s 1

# Export to JSON
python intelligent_vertical_creator.py analyze . --output report.json

# Run example
python example_intelligent_vertical_workflow.py 1
```

---

**Remember**: This tool suggests optimal configurations, but you know your use case best. Review suggestions and adjust as needed!
