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

# Add the src and config directories to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.extend([
    os.path.join(current_dir, 'src'),
    os.path.join(current_dir, 'config')
])

from sharepoint_sync import SharePointSync, SharePointSyncError
from azure_search_setup import AzureSearchSetup, SearchSetupError
from azure_search_integrated_vectorization import AzureSearchIntegratedVectorization
from settings import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('sync.log')
    ]
)
logger = logging.getLogger(__name__)

@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
def cli(debug):
    """SharePoint to Azure AI Search Sync Tool"""
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
@cli.command()
@click.option('--check-config', is_flag=True, help='Only check configuration without running sync')
def sync(check_config):
    """Sync SharePoint folder to Azure Blob Storage"""
    logger.info("Starting SharePoint sync operation...")
    
    try:
        # Check configuration
        if not config.validate_sharepoint_config():
            logger.error("SharePoint configuration is incomplete. Please check your .env file.")
            logger.error("Required: TENANT_ID, CLIENT_ID, SITE_ID, DRIVE_ID")
            sys.exit(1)
        
        if not config.validate_storage_config():
            logger.error("Azure Storage configuration is incomplete. Please check your .env file.")
            logger.error("Required: AZ_STORAGE_URL, AZ_CONTAINER")
            logger.error("Note: Ensure your app registration has 'Storage Blob Data Contributor' role")
            sys.exit(1)
        
        logger.info("Configuration validation passed")
        
        if check_config:
            print("✓ Configuration is valid")
            return
        
        # Run sync
        sp_sync = SharePointSync()
        summary = sp_sync.sync_sharepoint_folder()
        
        # Display results
        print("\\n=== Sync Summary ===")
        print(f"Total files found: {summary['total_files']}")
        print(f"Successfully processed: {summary['processed_files']}")
        print(f"Success rate: {summary['success_rate']:.1f}%")
        
        if summary['errors']:
            print(f"\\nErrors ({len(summary['errors'])}):")
            for error in summary['errors'][:5]:  # Show first 5 errors
                print(f"  - {error}")
            if len(summary['errors']) > 5:
                print(f"  ... and {len(summary['errors']) - 5} more errors")
        
        if summary['processed_files'] > 0:
            print("\\n✓ Sync completed successfully!")
            print("Next step: Run indexer to process documents in Azure AI Search")
        
    except SharePointSyncError as e:
        logger.error(f"SharePoint sync failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during sync: {e}")
        sys.exit(1)

@cli.command()
@click.option('--check-config', is_flag=True, help='Only check configuration without setting up search')
def setup_search(check_config):
    """Set up Azure AI Search pipeline with vector embeddings (data source, index, skillset, indexer)"""
    logger.info("Setting up Azure AI Search pipeline with vector embeddings...")
    
    try:
        # Check configuration
        if not config.validate_search_config():
            logger.error("Azure AI Search configuration is incomplete. Please check your .env file.")
            logger.error("Required: SEARCH_SERVICE_NAME, SEARCH_API_KEY, SEARCH_ENDPOINT")
            sys.exit(1)
        
        if not config.validate_storage_config():
            logger.error("Azure Storage configuration is incomplete. Please check your .env file.")
            logger.error("Required: AZ_STORAGE_URL, AZ_CONTAINER")
            logger.error("Note: Ensure your app registration has 'Storage Blob Data Contributor' role")
            sys.exit(1)
        
        if not config.validate_openai_config():
            logger.error("Azure OpenAI configuration is incomplete. Vector embeddings are required.")
            logger.error("Required: AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY")
            sys.exit(1)
        
        logger.info("Configuration validation passed - vector embeddings enabled")
        
        if check_config:
            print("✓ Configuration is valid")
            print("✓ Azure OpenAI configuration is valid for vector embeddings")
            print("✓ Using Service Principal authentication for Storage")
            return
        
        # Set up search pipeline
        search_setup = AzureSearchSetup()
        results = search_setup.setup_complete_pipeline()
        
        if "error" in results:
            logger.error(f"Search setup failed: {results['error']}")
            sys.exit(1)
        
        print("\\n=== Azure AI Search Pipeline Setup Complete ===")
        for resource_type, result in results.items():
            if isinstance(result, dict) and "name" in result:
                print(f"✓ {resource_type.capitalize()}: {result['name']}")
        
        print("\\n✓ Vector embeddings enabled for semantic search")
        print("\\nNext steps:")
        print("1. Run 'python main.py sync' to populate blob storage")
        print("2. Run 'python main.py run-indexer' to process documents")
        print("3. Configure Copilot Studio with your search service")
        
    except SearchSetupError as e:
        logger.error(f"Search setup failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error during search setup: {e}")
        sys.exit(1)

@cli.command()
@click.argument('name', default='ix-spofiles-v2')
def run_indexer(name):
    """Run the Azure AI Search indexer to process documents"""
    logger.info(f"Running indexer: {name}")
    
    try:
        search_setup = AzureSearchSetup()
        result = search_setup.run_indexer(name)
        print(f"✓ Indexer '{name}' started successfully")
        
        # Show initial status
        status = search_setup.get_indexer_status(name)
        if "lastResult" in status:
            last_result = status["lastResult"]
            print(f"Status: {last_result.get('status', 'Unknown')}")
            if "itemsProcessed" in last_result:
                print(f"Items processed in last run: {last_result['itemsProcessed']}")
        
        print(f"\\nUse 'python main.py indexer-status {name}' to monitor progress")
        
    except SearchSetupError as e:
        logger.error(f"Failed to run indexer: {e}")
        sys.exit(1)

@cli.command()
@click.argument('name', default='ix-spofiles-v2')
def indexer_status(name):
    """Check Azure AI Search indexer status and execution history"""
    try:
        search_setup = AzureSearchSetup()
        status = search_setup.get_indexer_status(name)
        
        print(f"\\n=== Indexer Status: {name} ===")
        print(f"Status: {status.get('status', 'Unknown')}")
        
        if "lastResult" in status:
            last_result = status["lastResult"]
            print(f"\\nLast Execution:")
            print(f"  Status: {last_result.get('status', 'Unknown')}")
            print(f"  Start Time: {last_result.get('startTime', 'Unknown')}")
            print(f"  End Time: {last_result.get('endTime', 'Unknown')}")
            print(f"  Items Processed: {last_result.get('itemsProcessed', 0)}")
            print(f"  Items Failed: {last_result.get('itemsFailed', 0)}")
            
            if "errors" in last_result and last_result["errors"]:
                print(f"\\nErrors ({len(last_result['errors'])}):")
                for error in last_result["errors"][:5]:  # Show first 5 errors
                    print(f"  - {error.get('errorMessage', 'Unknown error')}")
        
        if "executionHistory" in status:
            history = status["executionHistory"]
            print(f"\\nExecution History ({len(history)} runs):")
            for i, execution in enumerate(history[:3]):  # Show last 3 runs
                status_str = execution.get('status', 'Unknown')
                start_time = execution.get('startTime', 'Unknown')
                items = execution.get('itemsProcessed', 0)
                print(f"  {i+1}. {start_time} - {status_str} ({items} items)")
        
    except SearchSetupError as e:
        logger.error(f"Failed to check indexer status: {e}")
        sys.exit(1)

@cli.command()
def list_resources():
    """List all Azure AI Search resources"""
    try:
        search_setup = AzureSearchSetup()
        resources = search_setup.list_resources()
        
        print("\\n=== Azure AI Search Resources ===")
        for resource_type, items in resources.items():
            print(f"\\n{resource_type.capitalize()}:")
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
@click.option('--prefix', default='spo', help='Prefix for vertical resource set (stable names)')
def create_vertical(prefix):
    """Create or update a stable integrated vectorization vertical (ds/ss/idx/ix) and start indexing."""
    logger.info(f"Creating vertical with prefix '{prefix}'")
    try:
        search_setup = AzureSearchIntegratedVectorization()
        result = search_setup.create_vertical(prefix)
        print("\n=== Vertical Resources (Stable) ===")
        print(f"Data Source: {result['dataSource']}")
        print(f"Skillset   : {result['skillset']}")
        print(f"Index      : {result['index']}")
        print(f"Indexer    : {result['indexer']} (started)")
        print("\nNext steps:")
        print(f"1. Monitor: python main.py check-integrated-status")
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
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    cli()