#!/usr/bin/env python3
"""
Utility script for managing Azure AI Search resources.
"""

import sys
import os
import json
import logging
from typing import Dict, Any

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from azure_search_setup import AzureSearchSetup, SearchSetupError

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def setup_search_pipeline() -> None:
    """Set up the complete Azure AI Search pipeline with vector embeddings."""
    try:
        search_setup = AzureSearchSetup()
        results = search_setup.setup_complete_pipeline()
        
        if "error" in results:
            logger.error(f"Pipeline setup failed: {results['error']}")
            sys.exit(1)
        
        print("\\n=== Azure AI Search Pipeline Setup Complete ===")
        for resource_type, result in results.items():
            if isinstance(result, dict) and "name" in result:
                print(f"✓ {resource_type.capitalize()}: {result['name']}")
        
        print("\\n✓ Vector embeddings enabled for semantic search")
        print("\\nNext steps:")
        print("1. Run the SharePoint sync to populate blob storage")
        print("2. Check indexer status to monitor document processing")
        print("3. Configure Copilot Studio with your search service")
        
    except SearchSetupError as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)

def list_resources() -> None:
    """List all resources in the search service."""
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

def run_indexer(name: str = "ix-spofiles") -> None:
    """Run the indexer to process documents."""
    try:
        search_setup = AzureSearchSetup()
        result = search_setup.run_indexer(name)
        print(f"✓ Indexer '{name}' started successfully")
        
        # Show status
        status = search_setup.get_indexer_status(name)
        if "lastResult" in status:
            last_result = status["lastResult"]
            print(f"Last run status: {last_result.get('status', 'Unknown')}")
            if "itemsProcessed" in last_result:
                print(f"Items processed: {last_result['itemsProcessed']}")
        
    except SearchSetupError as e:
        logger.error(f"Failed to run indexer: {e}")
        sys.exit(1)

def check_indexer_status(name: str = "ix-spofiles") -> None:
    """Check indexer status and execution history."""
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
                print(f"  {i+1}. {execution.get('startTime', 'Unknown')} - {execution.get('status', 'Unknown')}")
        
    except SearchSetupError as e:
        logger.error(f"Failed to check indexer status: {e}")
        sys.exit(1)

def delete_resource(resource_type: str, name: str) -> None:
    """Delete a search service resource."""
    try:
        search_setup = AzureSearchSetup()
        
        print(f"Are you sure you want to delete {resource_type} '{name}'? (y/N): ", end="")
        response = input().strip().lower()
        
        if response == 'y':
            success = search_setup.delete_resource(resource_type, name)
            if success:
                print(f"✓ {resource_type} '{name}' deleted successfully")
            else:
                print(f"✗ Failed to delete {resource_type} '{name}'")
        else:
            print("Operation cancelled")
            
    except SearchSetupError as e:
        logger.error(f"Failed to delete resource: {e}")
        sys.exit(1)

def main():
    """Main entry point for the search management script."""
    if len(sys.argv) < 2:
        print("Usage: python search_manager.py <command> [options]")
        print("\\nCommands:")
        print("  setup                    - Set up complete search pipeline with vector embeddings")
        print("  list                     - List all search resources")
        print("  run-indexer [name]       - Run indexer (default: ix-spofiles)")
        print("  status [name]            - Check indexer status (default: ix-spofiles)")
        print("  delete <type> <name>     - Delete a resource (datasource, index, skillset, indexer)")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "setup":
        setup_search_pipeline()
    
    elif command == "list":
        list_resources()
    
    elif command == "run-indexer":
        name = sys.argv[2] if len(sys.argv) > 2 else "ix-spofiles"
        run_indexer(name)
    
    elif command == "status":
        name = sys.argv[2] if len(sys.argv) > 2 else "ix-spofiles"
        check_indexer_status(name)
    
    elif command == "delete":
        if len(sys.argv) < 4:
            print("Usage: python search_manager.py delete <type> <name>")
            print("Types: datasource, index, skillset, indexer")
            sys.exit(1)
        resource_type = sys.argv[2]
        name = sys.argv[3]
        delete_resource(resource_type, name)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()