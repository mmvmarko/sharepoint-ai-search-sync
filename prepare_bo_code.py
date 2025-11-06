"""
Prepare BO Code zip for Azure AI Search ingestion.

This script handles a zip structure with multiple API modules,
each containing swagger.json + generated code corpus.

Usage:
    python main.py prepare-bo-code --zip BO_Code.zip --out bo_prepared

Output:
    - bo_prepared/swagger/  -> All swagger.json files with metadata
    - bo_prepared/code/     -> All normalized code corpus files
"""

import os
import io
import json
import zipfile
import hashlib
from typing import List, Tuple, Dict, Any
from pathlib import Path

# File extensions to include in code corpus
CODE_EXTS = {
    '.ts', '.tsx', '.js', '.jsx', '.mjs', 
    '.json', '.md', '.html', '.css', '.scss', '.sass',
    '.py', '.java', '.cs', '.xml', '.yml', '.yaml',
    '.gradle', '.sh', '.bat', '.ps1', '.sql', '.d.ts'
}

# Extensions to skip (large generated files with minimal semantic value)
SKIP_EXTS = {
    '.map',  # source maps
    '.min.js', '.min.css',  # minified files
}


def _safe_name(name: str) -> str:
    """Sanitize a name for use as a filename."""
    return ''.join(c if c.isalnum() or c in ('-', '_', '.') else '_' for c in name)


def _hash_bytes(b: bytes) -> str:
    """Generate a short hash for content deduplication."""
    return hashlib.sha1(b).hexdigest()[:10]


def _normalize_text(b: bytes) -> str:
    """Best-effort decode bytes to text."""
    for enc in ('utf-8', 'utf-16', 'latin-1'):
        try:
            return b.decode(enc)
        except Exception:
            continue
    return b.decode('utf-8', errors='ignore')


def _extract_module_name(folder_path: str) -> str:
    """
    Extract module name from folder structure.
    E.g., 'BOPortal-API-client-CAMPAIGN' -> 'CAMPAIGN'
         'BOPortal-API-client' -> 'CORE'
    """
    parts = folder_path.split('/')
    if not parts:
        return 'UNKNOWN'
    
    folder = parts[0]
    if folder.startswith('BOPortal-API-client-'):
        module = folder.replace('BOPortal-API-client-', '')
        return module if module else 'CORE'
    elif folder == 'BOPortal-API-client':
        return 'CORE'
    return folder


def _should_include_file(file_path: str) -> bool:
    """Check if file should be included in code corpus."""
    ext = os.path.splitext(file_path)[1].lower()
    
    # Skip if explicitly in skip list
    for skip_ext in SKIP_EXTS:
        if file_path.lower().endswith(skip_ext):
            return False
    
    # Include if extension is in our allow list
    return ext in CODE_EXTS


def prepare_bo_code_from_zip(zip_path: str, out_dir: str) -> Dict[str, Any]:
    """
    Process BO Code zip and prepare two outputs:
    1. Swagger JSON files with enriched metadata
    2. Normalized code corpus text files
    
    Returns statistics about the processing.
    """
    os.makedirs(out_dir, exist_ok=True)
    
    # Create output subdirectories
    swagger_dir = os.path.join(out_dir, 'swagger')
    code_dir = os.path.join(out_dir, 'code')
    os.makedirs(swagger_dir, exist_ok=True)
    os.makedirs(code_dir, exist_ok=True)
    
    # Statistics tracking
    stats = {
        'modules_found': 0,
        'swagger_files': 0,
        'code_files_scanned': 0,
        'code_files_written': 0,
        'code_files_skipped': 0,
        'skipped_by_type': {},
        'modules': []
    }
    
    swagger_manifest = []
    code_manifest = []
    
    with zipfile.ZipFile(zip_path, 'r') as zf:
        # Group files by top-level folder (module)
        modules: Dict[str, List[zipfile.ZipInfo]] = {}
        
        for zi in zf.infolist():
            if zi.is_dir():
                continue
            
            parts = zi.filename.split('/')
            if len(parts) < 2:
                continue
            
            module_folder = parts[0]
            if module_folder not in modules:
                modules[module_folder] = []
            modules[module_folder].append(zi)
        
        stats['modules_found'] = len(modules)
        
        # Process each module
        for module_folder, files in modules.items():
            module_name = _extract_module_name(module_folder)
            module_stats = {
                'name': module_name,
                'folder': module_folder,
                'swagger': False,
                'code_files': 0
            }
            
            # Process swagger.json first
            swagger_file = next((f for f in files if f.filename.endswith('/swagger.json')), None)
            
            if swagger_file:
                swagger_data = zf.read(swagger_file)
                try:
                    swagger_obj = json.loads(swagger_data.decode('utf-8'))
                    
                    # Enrich with metadata
                    if 'info' not in swagger_obj:
                        swagger_obj['info'] = {}
                    
                    swagger_obj['info']['x-module'] = module_name
                    swagger_obj['info']['x-folder'] = module_folder
                    swagger_obj['info']['x-source-file'] = swagger_file.filename
                    
                    # Write enriched swagger JSON
                    safe_module = _safe_name(module_name)
                    swagger_out_name = f"swagger_{safe_module}.json"
                    swagger_out_path = os.path.join(swagger_dir, swagger_out_name)
                    
                    with open(swagger_out_path, 'w', encoding='utf-8') as sf:
                        json.dump(swagger_obj, sf, indent=2, ensure_ascii=False)
                    
                    stats['swagger_files'] += 1
                    module_stats['swagger'] = True
                    
                    api_title = swagger_obj.get('info', {}).get('title', module_name)
                    swagger_manifest.append(f"{module_name}: {api_title} -> {swagger_out_name}")
                    
                except Exception as e:
                    print(f"Warning: Failed to process swagger for {module_name}: {e}")
            
            # Process code files
            for zi in files:
                if zi.filename.endswith('/swagger.json'):
                    continue  # Already processed
                
                stats['code_files_scanned'] += 1
                
                if _should_include_file(zi.filename):
                    data = zf.read(zi)
                    text = _normalize_text(data)
                    
                    # Build output filename with module prefix
                    rel_path = zi.filename.replace(module_folder + '/', '', 1)
                    safe_rel = _safe_name(rel_path)
                    digest = _hash_bytes(data)
                    
                    # Format: <MODULE>__<safe_path>__<hash>.txt
                    out_name = f"{_safe_name(module_name)}__{safe_rel}__{digest}.txt"
                    out_path = os.path.join(code_dir, out_name)
                    
                    with open(out_path, 'w', encoding='utf-8', newline='\n') as cf:
                        # Add header for context
                        cf.write(f"# Source: {zi.filename}\n")
                        cf.write(f"# Module: {module_name}\n")
                        cf.write(f"# Folder: {module_folder}\n")
                        cf.write("#" + "=" * 70 + "\n\n")
                        cf.write(text)
                    
                    stats['code_files_written'] += 1
                    module_stats['code_files'] += 1
                    code_manifest.append(f"{zi.filename} -> {out_name}")
                else:
                    stats['code_files_skipped'] += 1
                    ext = os.path.splitext(zi.filename)[1].lower() or '(no ext)'
                    stats['skipped_by_type'][ext] = stats['skipped_by_type'].get(ext, 0) + 1
            
            stats['modules'].append(module_stats)
    
    # Write manifests
    swagger_manifest_path = os.path.join(swagger_dir, '_manifest.txt')
    with open(swagger_manifest_path, 'w', encoding='utf-8') as sm:
        sm.write(f"# Swagger JSON Files\n")
        sm.write(f"# Source: {zip_path}\n")
        sm.write(f"# Modules: {stats['modules_found']}\n")
        sm.write(f"# Files: {stats['swagger_files']}\n\n")
        sm.write('\n'.join(swagger_manifest))
    
    code_manifest_path = os.path.join(code_dir, '_manifest.txt')
    with open(code_manifest_path, 'w', encoding='utf-8') as cm:
        cm.write(f"# Code Corpus Files\n")
        cm.write(f"# Source: {zip_path}\n")
        cm.write(f"# Files written: {stats['code_files_written']}\n")
        cm.write(f"# Files skipped: {stats['code_files_skipped']}\n\n")
        for line in code_manifest:
            cm.write(line + '\n')
    
    # Write overall summary
    summary_path = os.path.join(out_dir, 'SUMMARY.txt')
    with open(summary_path, 'w', encoding='utf-8') as summary:
        summary.write("=" * 70 + "\n")
        summary.write("BO CODE PREPARATION SUMMARY\n")
        summary.write("=" * 70 + "\n\n")
        summary.write(f"Source ZIP: {zip_path}\n")
        summary.write(f"Output Directory: {out_dir}\n\n")
        
        summary.write("MODULES\n")
        summary.write("-" * 70 + "\n")
        summary.write(f"Total modules found: {stats['modules_found']}\n\n")
        for mod in stats['modules']:
            summary.write(f"  {mod['name']:<20} (Swagger: {'✓' if mod['swagger'] else '✗'}, Code files: {mod['code_files']})\n")
        
        summary.write(f"\nSWAGGER FILES\n")
        summary.write("-" * 70 + "\n")
        summary.write(f"Total: {stats['swagger_files']} files in {swagger_dir}\n\n")
        
        summary.write(f"CODE CORPUS\n")
        summary.write("-" * 70 + "\n")
        summary.write(f"Scanned: {stats['code_files_scanned']} files\n")
        summary.write(f"Written: {stats['code_files_written']} files in {code_dir}\n")
        summary.write(f"Skipped: {stats['code_files_skipped']} files\n")
        
        if stats['skipped_by_type']:
            summary.write(f"\nSkipped by type:\n")
            for ext, count in sorted(stats['skipped_by_type'].items(), key=lambda x: -x[1]):
                summary.write(f"  {ext:<15} : {count} files\n")
    
    return stats
