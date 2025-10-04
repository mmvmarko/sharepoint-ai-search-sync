import json
import logging
from typing import Dict, Any
import requests
from config.settings import config

# Set up logging
logger = logging.getLogger(__name__)

class SearchDebugger:
    """Debug Azure AI Search index and indexer issues."""
    
    def __init__(self):
        self.config = config
        self.headers = {
            "Content-Type": "application/json",
            "api-key": self.config.search_api_key
        }
        self.api_version = "2024-07-01"
    
    def _make_request(self, method: str, endpoint: str) -> Dict[str, Any]:
        """Make a request to Azure AI Search REST API."""
        url = f"{self.config.search_endpoint}/{endpoint}?api-version={self.api_version}"
        
        try:
            response = requests.get(url, headers=self.headers)
            
            if response.status_code in [200, 201, 202, 204]:
                try:
                    return response.json() if response.text else {"status": "success"}
                except json.JSONDecodeError:
                    return {"status": "success"}
            else:
                try:
                    error_data = response.json()
                except json.JSONDecodeError:
                    error_data = {"error": {"message": response.text}}
                return error_data
                
        except requests.exceptions.RequestException as e:
            return {"error": {"message": str(e)}}
    
    def check_index_documents(self, index_name: str = "idx-spofiles-integrated"):
        """Check how many documents are in the index."""
        print(f"🔍 Checking documents in index: {index_name}")
        
        # Get document count
        result = self._make_request("GET", f"indexes/{index_name}/docs/$count")
        
        if isinstance(result, dict) and "error" in result:
            print(f"❌ Error getting document count: {result['error'].get('message', 'Unknown error')}")
            return
        
        # Handle the count response
        if isinstance(result, int):
            count = result
        elif isinstance(result, dict):
            count = result.get('value', result.get('@odata.count', 0))
        else:
            count = 0
            
        print(f"📊 Document count: {count}")
        
        if count == 0:
            print("⚠️  Index is empty!")
        else:
            # Get a few sample documents
            sample_result = self._make_request("GET", f"indexes/{index_name}/docs?$top=3&$select=id,title,content")
            
            if isinstance(sample_result, dict) and "error" not in sample_result and "value" in sample_result:
                print(f"📄 Sample documents:")
                for doc in sample_result["value"]:
                    print(f"  • ID: {doc.get('id', 'N/A')}")
                    print(f"    Title: {doc.get('title', 'N/A')}")
                    content_preview = (doc.get('content', '')[:100] + '...') if doc.get('content') else 'No content'
                    print(f"    Content: {content_preview}")
                    print()
            else:
                print("⚠️  Could not retrieve sample documents")
    
    def check_indexer_detailed_status(self, indexer_name: str = "ix-spofiles-integrated"):
        """Get detailed indexer execution history."""
        print(f"🔍 Checking detailed status for indexer: {indexer_name}")
        
        result = self._make_request("GET", f"indexers/{indexer_name}/status")
        
        if "error" in result:
            print(f"❌ Error getting indexer status: {result['error'].get('message', 'Unknown error')}")
            return
        
        print(f"📊 Indexer Status: {result.get('status', 'unknown')}")
        
        # Check execution history
        if "executionHistory" in result:
            print("📜 Execution History:")
            for i, execution in enumerate(result["executionHistory"][:3]):  # Last 3 executions
                print(f"\n  Execution #{i+1}:")
                print(f"    Status: {execution.get('status', 'unknown')}")
                print(f"    Start: {execution.get('startTime', 'N/A')}")
                print(f"    End: {execution.get('endTime', 'N/A')}")
                print(f"    Items Processed: {execution.get('itemsProcessed', 0)}")
                print(f"    Items Failed: {execution.get('itemsFailed', 0)}")
                
                if execution.get('errors'):
                    print(f"    Errors:")
                    for error in execution['errors'][:3]:
                        print(f"      • {error.get('errorMessage', 'Unknown error')}")
                        print(f"        Key: {error.get('key', 'N/A')}")
                
                if execution.get('warnings'):
                    print(f"    Warnings:")
                    for warning in execution['warnings'][:3]:
                        print(f"      • {warning.get('message', 'Unknown warning')}")
    
    def check_data_source_connection(self, ds_name: str = "ds-spofiles-integrated"):
        """Check if data source can connect to storage."""
        print(f"🔍 Checking data source: {ds_name}")
        
        result = self._make_request("GET", f"datasources/{ds_name}")
        
        if "error" in result:
            print(f"❌ Error getting data source: {result['error'].get('message', 'Unknown error')}")
            return
        
        print(f"✅ Data source exists")
        print(f"    Type: {result.get('type', 'N/A')}")
        print(f"    Container: {result.get('container', {}).get('name', 'N/A')}")
        
        # The connection string will be masked in the response for security
        credentials = result.get('credentials', {})
        if 'connectionString' in credentials:
            print(f"    Connection configured: Yes")
        else:
            print(f"    Connection configured: No")
    
    def check_index_configuration(self, index_name: str = "idx-spofiles-integrated"):
        """Check index field configuration."""
        print(f"🔍 Checking index configuration: {index_name}")
        
        result = self._make_request("GET", f"indexes/{index_name}")
        
        if "error" in result:
            print(f"❌ Error getting index: {result['error'].get('message', 'Unknown error')}")
            return
        
        print(f"✅ Index exists")
        
        # Check fields
        fields = result.get('fields', [])
        print(f"📋 Fields ({len(fields)}):")
        for field in fields:
            field_type = field.get('type', 'unknown')
            is_key = field.get('key', False)
            is_searchable = field.get('searchable', False)
            is_vector = 'Collection(Edm.Single)' in field_type
            
            key_indicator = " [KEY]" if is_key else ""
            search_indicator = " [SEARCHABLE]" if is_searchable else ""
            vector_indicator = " [VECTOR]" if is_vector else ""
            
            print(f"  • {field.get('name', 'unnamed')}: {field_type}{key_indicator}{search_indicator}{vector_indicator}")
        
        # Check vector configuration
        vector_search = result.get('vectorSearch', {})
        if vector_search:
            print(f"🔍 Vector Search Configuration:")
            vectorizers = vector_search.get('vectorizers', [])
            if vectorizers:
                print(f"  Vectorizers: {len(vectorizers)}")
                for vectorizer in vectorizers:
                    print(f"    • {vectorizer.get('name', 'unnamed')} ({vectorizer.get('kind', 'unknown')})")
            else:
                print(f"  ⚠️  No vectorizers configured!")
    
    def run_full_diagnosis(self):
        """Run complete diagnosis of the search pipeline."""
        print("🏥 Running Full Diagnosis of Azure AI Search Pipeline")
        print("=" * 60)
        
        self.check_data_source_connection()
        print()
        
        self.check_index_configuration()
        print()
        
        self.check_indexer_detailed_status()
        print()
        
        self.check_index_documents()
        print()
        
        print("🏁 Diagnosis Complete")

if __name__ == "__main__":
    debugger = SearchDebugger()
    debugger.run_full_diagnosis()