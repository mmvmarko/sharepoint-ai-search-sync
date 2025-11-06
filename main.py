#!/usr/bin/env python3
"""
SharePoint to Azure AI Search Sync Application

This application syncs SharePoint Online documents to Azure Blob Storage
and configures Azure AI Search for indexing and searching the content.
"""

import sys
import os
import logging
import json
import click
from typing import Dict, Any

# Treat repository as a namespace: ensure parent directory is on path once
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.sharepoint_sync import SharePointSync, SharePointSyncError
from src.azure_search_setup import AzureSearchSetup, SearchSetupError
from src.azure_search_integrated_vectorization import AzureSearchIntegratedVectorization
from config.settings import config
from prepare_code_corpus import prepare_code_from_zip
from prepare_bo_code import prepare_bo_code_from_zip

logger = logging.getLogger(__name__)

# --------------------------------------------------
# Click root group
# --------------------------------------------------
@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
def cli(debug: bool = False):
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

# --------------------------------------------------
# Helper for generic indexer run
# --------------------------------------------------
def _run_indexer_generic(name: str):
    """Attempt to run indexer with integrated client; fall back to legacy."""
    try:
        iv = AzureSearchIntegratedVectorization()
        iv.run_indexer(name)
        return iv.get_indexer_status(name)
    except Exception:
        legacy = AzureSearchSetup()
        legacy.run_indexer(name)
        return legacy.get_indexer_status(name)

@cli.command('run-indexer')
@click.argument('name')
def run_indexer(name):
    """Run any indexer (legacy or integrated)."""
    logger.info(f"Running indexer: {name}")
    try:
        status = _run_indexer_generic(name)
        last = status.get('lastResult', {})
        print(f"✓ Indexer '{name}' triggered")
        if last:
            print(f"Last run status: {last.get('status','unknown')} itemsProcessed={last.get('itemsProcessed')} failed={last.get('itemsFailed')}")
        print(f"Use: python main.py indexer-status {name}")
    except Exception as e:
        logger.error(f"Failed to run indexer: {e}")
        print(f"❌ Failed to run indexer: {e}")
        sys.exit(1)

@cli.command('indexer-status')
@click.argument('name')
def indexer_status(name):
    """Show status/history for any indexer (legacy or integrated)."""
    try:
        try:
            iv = AzureSearchIntegratedVectorization()
            status = iv.get_indexer_status(name)
        except Exception:
            setup = AzureSearchSetup()
            status = setup.get_indexer_status(name)

        print(f"\n=== Indexer Status: {name} ===")
        print(f"Overall Status: {status.get('status','unknown')}")
        last = status.get('lastResult', {})
        if last:
            print("\nLast Run:")
            print(f"  Status          : {last.get('status')}")
            print(f"  Start Time      : {last.get('startTime')}")
            print(f"  End Time        : {last.get('endTime')}")
            print(f"  Items Processed : {last.get('itemsProcessed')}")
            print(f"  Items Failed    : {last.get('itemsFailed')}")
            errs = last.get('errors') or []
            if errs:
                print(f"  Errors ({len(errs)} up to 5 shown):")
                for err in errs[:5]:
                    print(f"    - {err.get('errorMessage','?')}")
        history = status.get('executionHistory') or []
        if history:
            print(f"\nRecent Executions ({min(5,len(history))}):")
            for i, h in enumerate(history[:5]):
                print(f"  {i+1}. {h.get('startTime')} -> {h.get('status')} items={h.get('itemsProcessed')}")
    except Exception as e:
        logger.error(f"Failed to check indexer status: {e}")
        print(f"❌ Failed to check indexer status: {e}")
        sys.exit(1)

@cli.command(name='prepare-code')
@click.option('--zip', 'zip_path', required=True, help='Path to a zip file containing the project code')
@click.option('--project-name', required=True, help='Human-readable project name (used in folder name)')
@click.option('--project-code', required=True, help='Short code or org tag for the project')
@click.option('--out', 'out_dir', required=True, help='Output directory where the corpus will be written')
def prepare_code(zip_path: str, project_name: str, project_code: str, out_dir: str):
    """Unpack a project zip and emit normalized .txt files as a code corpus suitable for indexing."""
    try:
        result = prepare_code_from_zip(zip_path, project_name, project_code, out_dir)
        dest = result['project_folder']
        scanned = result['scanned']
        produced = result['collected']
        skipped = result['skipped']
        skipped_types = result['skipped_types']
        print("\n=== Code Corpus Prepared ===")
        print(f"Project    : {project_name} ({project_code})")
        print(f"Source Zip : {zip_path}")
        print(f"Output Dir : {dest}")
        print(f"Scanned    : {scanned} files")
        print(f"Collected  : {produced} text files")
        print(f"Skipped    : {skipped} files")
        if skipped > 0 and skipped_types:
            kinds = ', '.join(f"{k}:{v}" for k, v in sorted(skipped_types.items()))
            print(f"Skipped by type: {kinds}")
        print("\nArtifacts:")
        print(f"  - {os.path.join(dest, 'code_corpus_manifest.txt')}")
        print(f"  - {os.path.join(dest, 'file_map.txt')}")
    except Exception as e:
        logger.error(f"Failed to prepare code corpus: {e}")
        print(f"❌ Failed to prepare code corpus: {e}")
        sys.exit(1)


@cli.command(name='prepare-bo-code')
@click.option('--zip', 'zip_path', required=True, help='Path to BO_Code.zip containing multiple API modules')
@click.option('--out', 'out_dir', required=True, help='Output directory for prepared files')
def prepare_bo_code(zip_path: str, out_dir: str):
    """
    Prepare BO Code zip for Azure AI Search ingestion.
    
    Processes a zip containing multiple API modules (each with swagger.json + code corpus).
    Creates two outputs:
      - swagger/  -> Enriched OpenAPI/Swagger JSON files
      - code/     -> Normalized code corpus text files
    """
    try:
        print(f"📦 Processing BO Code zip: {zip_path}")
        print(f"📁 Output directory: {out_dir}\n")
        
        stats = prepare_bo_code_from_zip(zip_path, out_dir)
        
        print("\n" + "=" * 70)
        print("✅ BO CODE PREPARATION COMPLETE")
        print("=" * 70)
        print(f"\n📊 STATISTICS")
        print(f"  Modules found     : {stats['modules_found']}")
        print(f"  Swagger files     : {stats['swagger_files']}")
        print(f"  Code files scanned: {stats['code_files_scanned']}")
        print(f"  Code files written: {stats['code_files_written']}")
        print(f"  Code files skipped: {stats['code_files_skipped']}")
        
        if stats['skipped_by_type']:
            print(f"\n  Skipped by type:")
            for ext, count in sorted(stats['skipped_by_type'].items(), key=lambda x: -x[1])[:10]:
                print(f"    {ext:<15} : {count} files")
        
        print(f"\n📂 OUTPUT STRUCTURE")
        print(f"  {os.path.join(out_dir, 'swagger')}  -> {stats['swagger_files']} JSON files")
        print(f"  {os.path.join(out_dir, 'code')}     -> {stats['code_files_written']} text files")
        print(f"  {os.path.join(out_dir, 'SUMMARY.txt')}  -> Full report")
        
        print(f"\n📋 MODULES ({stats['modules_found']})")
        for mod in stats['modules'][:10]:  # Show first 10
            swagger_check = '✓' if mod['swagger'] else '✗'
            print(f"  {mod['name']:<20} Swagger: {swagger_check}  Code: {mod['code_files']} files")
        
        if len(stats['modules']) > 10:
            print(f"  ... and {len(stats['modules']) - 10} more modules")
        
        print(f"\n🎯 NEXT STEPS")
        print(f"  1. Review SUMMARY.txt in output directory")
        print(f"  2. Upload swagger/ folder to blob container for OpenAPI vertical")
        print(f"  3. Upload code/ folder to blob container for code vertical")
        print(f"  4. Create integrated vectorization indexes with:")
        print(f"     python main.py create_vertical --prefix bo-swagger --json-only --json-container <container>")
        print(f"     python main.py create_vertical --prefix bo-code")
        
    except Exception as e:
        logger.error(f"Failed to prepare BO code: {e}", exc_info=True)
        print(f"❌ Failed to prepare BO code: {e}")
        sys.exit(1)


@cli.command()
def list_resources():
    """List all Azure AI Search resources"""
    try:
        search_setup = AzureSearchSetup()
        resources = search_setup.list_resources()
        print("\n=== Azure AI Search Resources ===")
        for resource_type, items in resources.items():
            print(f"\n{resource_type.capitalize()}:")
            if items:
                for item in items:
                    print(f"  - {item}")
            else:
                print("  (none)")
    except SearchSetupError as e:
        logger.error(f"Failed to list resources: {e}")
        sys.exit(1)

@cli.command()
def full_setup():
    """Run complete setup: SharePoint sync + Azure AI Search configuration"""
    logger.info("Starting full setup process...")
    
    try:
        # Validate all configurations
        config_issues = []
        
        if not config.validate_sharepoint_config():
            config_issues.append("SharePoint configuration (TENANT_ID, CLIENT_ID, SITE_ID, DRIVE_ID)")
        
        if not config.validate_storage_config():
            config_issues.append("Azure Storage configuration (AZ_STORAGE_URL, AZ_CONTAINER) + Storage Blob Data Contributor role")
        
        if not config.validate_search_config():
            config_issues.append("Azure AI Search configuration (SEARCH_SERVICE_NAME, SEARCH_API_KEY, SEARCH_ENDPOINT)")
        
        if not config.validate_openai_config():
            config_issues.append("Azure OpenAI configuration (AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY)")
        
        if config_issues:
            logger.error("Configuration incomplete:")
            for issue in config_issues:
                logger.error(f"  - {issue}")
            sys.exit(1)
        
        print("✓ All configurations validated")
        
        # Step 1: Set up Azure AI Search
        print("\\n=== Step 1: Setting up Azure AI Search with Vector Embeddings ===")
        search_setup = AzureSearchSetup()
        
        search_results = search_setup.setup_complete_pipeline()
        
        if "error" in search_results:
            logger.error(f"Search setup failed: {search_results['error']}")
            sys.exit(1)
        
        print("✓ Azure AI Search pipeline created with vector embeddings")
        
        # Step 2: Sync SharePoint
        print("\\n=== Step 2: Syncing SharePoint content ===")
        sp_sync = SharePointSync()
        summary = sp_sync.sync_sharepoint_folder()
        
        print(f"✓ Processed {summary['processed_files']}/{summary['total_files']} files")
        
        if summary['errors']:
            logger.warning(f"{len(summary['errors'])} files had errors during sync")
        
        # Step 3: Run indexer
        if summary['processed_files'] > 0:
            print("\\n=== Step 3: Processing documents in Azure AI Search ===")
            search_setup.run_indexer()
            print("✓ Indexer started")
            
            print("\\n=== Setup Complete! ===")
            print("Your SharePoint content is now being indexed for search.")
            print("\\nNext steps:")
            print("1. Monitor indexer progress: python main.py indexer-status")
            print("2. Configure Copilot Studio with your search service")
            print("3. Test search functionality")
        else:
            print("\\n⚠ No files were processed. Check your SharePoint configuration.")
        
    except (SharePointSyncError, SearchSetupError) as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during setup: {e}")
        sys.exit(1)

@cli.command()
def config_info():
    """Show current configuration status"""
    print("\\n=== Configuration Status ===")
    
    # SharePoint config
    sp_valid = config.validate_sharepoint_config()
    print(f"SharePoint: {'✓' if sp_valid else '✗'}")
    if not sp_valid:
        print("  Missing: TENANT_ID, CLIENT_ID, SITE_ID, or DRIVE_ID")
    
    # Storage config
    storage_valid = config.validate_storage_config()
    print(f"Azure Storage: {'✓' if storage_valid else '✗'}")
    if not storage_valid:
        print("  Missing: AZ_STORAGE_URL or AZ_CONTAINER")
        print("  Note: Ensure app registration has 'Storage Blob Data Contributor' role")
    
    # Search config
    search_valid = config.validate_search_config()
    print(f"Azure AI Search: {'✓' if search_valid else '✗'}")
    if not search_valid:
        print("  Missing: SEARCH_SERVICE_NAME, SEARCH_API_KEY, or SEARCH_ENDPOINT")
    
    # Azure OpenAI (required for vector embeddings)
    openai_valid = config.validate_openai_config()
    print(f"Azure OpenAI (required): {'✓' if openai_valid else '✗'}")
    if not openai_valid:
        print("  Missing: AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY")
        print("  Vector embeddings are mandatory for this application")
    
    print(f"\\nConfiguration file: {os.path.join(os.getcwd(), '.env')}")
    if not os.path.exists('.env'):
        print("⚠ .env file not found. Copy .env.template to .env and configure it.")

@cli.command()
def setup_integrated_vectorization():
    """Set up Azure AI Search with integrated vectorization for Copilot Studio"""
    logger.info("Setting up Azure AI Search with integrated vectorization...")
    
    try:
        search_setup = AzureSearchIntegratedVectorization()
        
        # Set up the complete pipeline
        result = search_setup.setup_integrated_vectorization_pipeline()
        
        if result.get("status") == "success":
            print("\n🎉 Integrated vectorization pipeline setup completed!")
            print("\n📋 Resources created:")
            print("   • Data source: ds-spofiles-integrated")
            print("   • Index: idx-spofiles-integrated (with integrated vectorization)")
            print("   • Indexer: ix-spofiles-integrated")
            print("\n➡ Monitor progress: python main.py check-integrated-status")
        else:
            print("\n⚠ Setup returned unexpected status. Check logs.")
    except SearchSetupError as e:
        logger.error(f"Failed to check status: {e}")
        print(f"\n❌ Failed to check status: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

@cli.command(name='test_integrated')  # Preserve underscore form so user can run `test_integrated`
@click.option('--prefix', default='test', help='Prefix for disposable test resources')
def test_integrated(prefix):
    """Create a disposable integrated vectorization pipeline (data source, index, skillset, indexer) for testing."""
    logger.info("Creating disposable integrated vectorization resources for test...")
    try:
        search_setup = AzureSearchIntegratedVectorization()
        result = search_setup.quick_test_setup(prefix=prefix)
        print("\n=== Quick Integrated Vectorization Test Resources ===")
        print(f"Data Source: {result['dataSource']}")
        print(f"Index     : {result['index']}")
        print(f"Skillset  : {result['skillset']}")
        print(f"Indexer   : {result['indexer']} (started)")
        print("\nNext steps:")
        print(f"1. Monitor: python main.py check-integrated-status")
        print(f"2. After processing, verify vectors via REST vectorQueries on index {result['index']}")
        print("3. Delete test resources manually when done to save capacity.")
    except SearchSetupError as e:
        logger.error(f"Test setup failed: {e}")
        sys.exit(1)

@cli.command(name='create_vertical')
@click.option('--prefix', default='spo', help='Prefix for vertical resource set (fallback for names)')
@click.option('--container', default=None, help='Override blob container name (defaults to AZ_CONTAINER)')
@click.option('--json-container', default=None, help='Override blob container for JSON vertical when --split-json is used')
@click.option('--ds-name', default=None, help='Explicit data source name (optional)')
@click.option('--ss-name', default=None, help='Explicit skillset name (optional)')
@click.option('--idx-name', default=None, help='Explicit index name (optional)')
@click.option('--ix-name', default=None, help='Explicit indexer name (optional)')
@click.option('--split-json', is_flag=True, default=False, help='Create separate -json vertical for .json files')
@click.option('--json-only', is_flag=True, default=False, help='Create only the -json vertical (no base vertical)')
def create_vertical(prefix, container, json_container, ds_name, ss_name, idx_name, ix_name, split_json, json_only):
    """Create or update an integrated vectorization vertical with customizable names.

    If explicit names are not provided they are derived from prefix:
      ds-{prefix}, ss-{prefix}, idx-{prefix}, ix-{prefix}
    """
    logger.info(f"Creating vertical with prefix='{prefix}' container='{container}' explicit names ds={ds_name} ss={ss_name} idx={idx_name} ix={ix_name}")
    try:
        if split_json and json_only:
            raise SearchSetupError("--split-json and --json-only are mutually exclusive. Use one or the other.")
        search_setup = AzureSearchIntegratedVectorization()
        result = search_setup.create_vertical(
            prefix,
            container=container,
            json_container=json_container,
            data_source_name=ds_name,
            skillset_name=ss_name,
            index_name=idx_name,
            indexer_name=ix_name,
            create_json_vertical=split_json,
            json_only=json_only
        )
        if json_only:
            print("\n=== JSON-Only Vertical Resources ===")
            jr = result.get('json', {})
            print(f"Data Source: {jr.get('dataSource')}")
            print(f"Skillset   : {jr.get('skillset')}")
            print(f"Index      : {jr.get('index')}")
            print(f"Indexer    : {jr.get('indexer')} (started)")
            if json_container or container:
                print(f"Container  : {json_container or container}")
        else:
            print("\n=== Vertical Resources (Stable) ===")
            print(f"Data Source: {result['dataSource']}")
            print(f"Skillset   : {result['skillset']}")
            print(f"Index      : {result['index']}")
            print(f"Indexer    : {result['indexer']} (started)")
            if container:
                print(f"Container  : {container}")
        if result.get('json'):
            jr = result['json']
            print("\n--- JSON Vertical ---")
            print(f"Data Source: {jr['dataSource']}")
            print(f"Skillset   : {jr['skillset']}")
            print(f"Index      : {jr['index']}")
            print(f"Indexer    : {jr['indexer']} (started)")
            if json_container:
                print(f"Container  : {json_container}")
        print("\nNext steps:")
        print("1. Monitor: python main.py check-integrated-status")
        print(f"2. Run a vector query against index {result['index']} when status shows success")
        print("3. Use this index as knowledge source in Copilot Studio if desired")
    except SearchSetupError as e:
        logger.error(f"Vertical creation failed: {e}")
        sys.exit(1)

@cli.command(name='delete_vertical')
@click.option('--prefix', default='spo', help='Prefix of vertical (stable names) to delete')
def delete_vertical(prefix):
    """Delete all search resources (data source, skillset, index, indexer) for a given prefix."""
    logger.info(f"Deleting vertical with prefix '{prefix}'")
    try:
        search_setup = AzureSearchIntegratedVectorization()
        report = search_setup.delete_vertical(prefix)
        print("\n=== Deletion Report ===")
        for kind, info in report['resources'].items():
            status = info['status']
            name = info['name']
            print(f"{kind:10s} {name:40s} -> {status}")
        print("\nCompleted deletion attempt.")
    except SearchSetupError as e:
        logger.error(f"Deletion failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

# Manual aliases for convenience (underscore forms)
cli.add_command(run_indexer, name='run_indexer')
cli.add_command(indexer_status, name='indexer_status')

if __name__ == '__main__':
    cli()