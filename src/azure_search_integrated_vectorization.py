import json
import logging
from typing import Dict, Any, List, Optional
import requests
from config.settings import config

# Set up logging
logger = logging.getLogger(__name__)

class SearchSetupError(Exception):
    """Custom exception for Azure AI Search setup operations."""
    pass

class AzureSearchIntegratedVectorization:
    """Handles Azure AI Search configuration with integrated vectorization for Copilot Studio."""
    
    def __init__(self):
        self.config = config
        
        if not self.config.validate_search_config():
            raise SearchSetupError("Azure AI Search configuration is incomplete. Check your .env file.")
        
        if not self.config.validate_openai_config():
            raise SearchSetupError("Azure OpenAI configuration is incomplete. Vector embeddings are required. Check your .env file.")
        
        self.headers = {
            "Content-Type": "application/json",
            "api-key": self.config.search_api_key
        }
        self.api_version = "2024-07-01"
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a request to Azure AI Search REST API."""
        url = f"{self.config.search_endpoint}/{endpoint}?api-version={self.api_version}"
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=self.headers)
            elif method.upper() == "POST":
                response = requests.post(url, headers=self.headers, json=data)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=self.headers, json=data)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=self.headers)
            else:
                raise SearchSetupError(f"Unsupported HTTP method: {method}")
            
            # Handle different response codes
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
                
                logger.error(f"Request failed with status {response.status_code}: {error_data}")
                return error_data
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            raise SearchSetupError(f"HTTP request failed: {str(e)}")

    def create_data_source(self, name: str = "ds-spofiles-integrated") -> Dict[str, Any]:
        """Create Azure Storage data source."""
        logger.info(f"Creating data source: {name}")
        
        if not self.config.validate_storage_config():
            raise SearchSetupError("Azure Storage configuration is incomplete. Check your .env file.")
        
        # Build connection string - use account key if available, otherwise managed identity
        if self.config.az_storage_account_key and self.config.az_storage_account_key != "your_storage_account_key_here":
            connection_string = f"DefaultEndpointsProtocol=https;AccountName={self.config.storage_account_name};AccountKey={self.config.az_storage_account_key};EndpointSuffix=core.windows.net"
        else:
            # Use managed identity (requires proper Azure setup)
            connection_string = f"DefaultEndpointsProtocol=https;AccountName={self.config.storage_account_name};EndpointSuffix=core.windows.net"
        
        data_source_definition = {
            "name": name,
            "type": "azureblob",
            "credentials": {
                "connectionString": connection_string
            },
            "container": {
                "name": self.config.az_container
            },
            "description": "SharePoint files storage for integrated vectorization"
        }
        
        result = self._make_request("PUT", f"datasources/{name}", data_source_definition)
        
        if "error" in result:
            if result.get("error", {}).get("code") == "ResourceNotFound":
                logger.error("Search service not found. Check your search endpoint and API key.")
            raise SearchSetupError(f"Failed to create data source: {result}")
        
        logger.info(f"Successfully created data source: {name}")
        return result

    def create_index_with_integrated_vectorization(self, name: str = "idx-spofiles-integrated") -> Dict[str, Any]:
        """Create search index with integrated vectorization for Copilot Studio compatibility."""
        logger.info(f"Creating index with integrated vectorization: {name}")
        
        fields = [
            {
                "name": "id",
                "type": "Edm.String",
                "key": True,
                "filterable": True,
                "searchable": False,
                "retrievable": True
            },
            {
                "name": "title",
                "type": "Edm.String",
                "searchable": True,
                "filterable": False,
                "retrievable": True,
                "analyzer": "standard.lucene"
            },
            {
                "name": "content",
                "type": "Edm.String",
                "searchable": True,
                "filterable": False,
                "sortable": False,
                "facetable": False,
                "retrievable": True,
                "analyzer": "standard.lucene"
            },
            {
                "name": "source_url",
                "type": "Edm.String",
                "searchable": False,
                "filterable": True,
                "retrievable": True
            },
            {
                "name": "lastModified",
                "type": "Edm.DateTimeOffset",
                "filterable": True,
                "sortable": True,
                "retrievable": True
            },
            {
                "name": "size",
                "type": "Edm.Int64",
                "filterable": True,
                "sortable": True,
                "retrievable": True
            },
            {
                "name": "file_extension",
                "type": "Edm.String",
                "filterable": True,
                "facetable": True,
                "retrievable": True
            },
            {
                "name": "content_vector",
                "type": "Collection(Edm.Single)",
                "searchable": True,
                "retrievable": True,  # FIXED: Made retrievable for proper integrated vectorization
                "dimensions": 1536,  # text-embedding-3-small dimensions
                "vectorSearchProfile": "default-vector-profile"
            }
        ]
        
        # Integrated vectorization configuration
        index_definition = {
            "name": name,
            "fields": fields,
            "vectorSearch": {
                "algorithms": [
                    {
                        "name": "default-hnsw-algorithm",
                        "kind": "hnsw",
                        "hnswParameters": {
                            "metric": "cosine",
                            "m": 4,
                            "efConstruction": 400,
                            "efSearch": 500
                        }
                    }
                ],
                "profiles": [
                    {
                        "name": "default-vector-profile",
                        "algorithm": "default-hnsw-algorithm",
                        "vectorizer": "default-vectorizer"
                    }
                ],
                "vectorizers": [
                    {
                        "name": "default-vectorizer",
                        "kind": "azureOpenAI",
                        "azureOpenAIParameters": {
                            "resourceUri": self.config.azure_openai_endpoint,
                            "deploymentId": self.config.azure_openai_embedding_model,
                            "apiKey": self.config.azure_openai_api_key,
                            "modelName": "text-embedding-3-small"
                        }
                    }
                ]
            }
        }
        
        # Use PUT to create or update the index
        result = self._make_request("PUT", f"indexes/{name}", index_definition)
        
        if "error" in result:
            raise SearchSetupError(f"Failed to create index: {result}")
        
        logger.info(f"Successfully created index with integrated vectorization: {name}")
        return result

    def create_indexer_with_integrated_vectorization(self, name: str = "ix-spofiles-integrated", 
                                                   data_source_name: str = "ds-spofiles-integrated",
                                                   index_name: str = "idx-spofiles-integrated") -> Dict[str, Any]:
        """Create indexer with integrated vectorization - no skillset needed."""
        logger.info(f"Creating indexer with integrated vectorization: {name}")
        
        indexer_definition = {
            "name": name,
            "dataSourceName": data_source_name,
            "targetIndexName": index_name,
            "parameters": {
                "configuration": {
                    "dataToExtract": "contentAndMetadata",
                    "parsingMode": "default",
                    "indexedFileNameExtensions": ".pdf,.docx,.pptx,.txt,.xlsx,.html,.md",
                    "excludedFileNameExtensions": ".json,.xml",
                    "failOnUnsupportedContentType": False,
                    "failOnUnprocessableDocument": False
                }
            },
            "fieldMappings": [
                {
                    "sourceFieldName": "metadata_storage_path",
                    "targetFieldName": "id",
                    "mappingFunction": {
                        "name": "base64Encode"
                    }
                },
                {
                    "sourceFieldName": "metadata_storage_name",
                    "targetFieldName": "title"
                },
                {
                    "sourceFieldName": "content",
                    "targetFieldName": "content"
                },
                {
                    "sourceFieldName": "metadata_storage_path",
                    "targetFieldName": "source_url"
                },
                {
                    "sourceFieldName": "metadata_storage_last_modified",
                    "targetFieldName": "lastModified"
                },
                {
                    "sourceFieldName": "metadata_storage_size",
                    "targetFieldName": "size"
                },
                {
                    "sourceFieldName": "metadata_storage_file_extension",
                    "targetFieldName": "file_extension"
                }
            ]
        }
        
        # Use PUT to create or update the indexer
        result = self._make_request("PUT", f"indexers/{name}", indexer_definition)
        
        if "error" in result:
            raise SearchSetupError(f"Failed to create indexer: {result}")
        
        logger.info(f"Successfully created indexer with integrated vectorization: {name}")
        return result

    def run_indexer(self, name: str) -> Dict[str, Any]:
        """Run the indexer to process documents."""
        logger.info(f"Running indexer: {name}")
        
        result = self._make_request("POST", f"indexers/{name}/run")
        
        if "error" in result:
            raise SearchSetupError(f"Failed to run indexer: {result}")
        
        logger.info(f"Successfully started indexer: {name}")
        return result

    def get_indexer_status(self, name: str) -> Dict[str, Any]:
        """Get indexer execution status."""
        logger.info(f"Getting status for indexer: {name}")
        
        result = self._make_request("GET", f"indexers/{name}/status")
        
        if "error" in result:
            raise SearchSetupError(f"Failed to get indexer status: {result}")
        
        return result

    def setup_integrated_vectorization_pipeline(self) -> Dict[str, Any]:
        """Set up complete Azure AI Search pipeline with integrated vectorization."""
        logger.info("Setting up Azure AI Search pipeline with integrated vectorization")
        
        try:
            # Create data source
            ds_result = self.create_data_source()
            logger.info("✓ Data source created")
            
            # Create index with integrated vectorization
            index_result = self.create_index_with_integrated_vectorization()
            logger.info("✓ Index with integrated vectorization created")
            
            # Create indexer
            indexer_result = self.create_indexer_with_integrated_vectorization()
            logger.info("✓ Indexer with integrated vectorization created")
            
            # Run indexer
            run_result = self.run_indexer("ix-spofiles-integrated")
            logger.info("✓ Indexer started")
            
            logger.info("Azure AI Search pipeline with integrated vectorization setup completed successfully!")
            logger.info("This index is now compatible with Copilot Studio.")
            
            return {
                "status": "success",
                "data_source": ds_result,
                "index": index_result,
                "indexer": indexer_result,
                "run": run_result
            }
            
        except SearchSetupError as e:
            logger.error(f"Failed to setup pipeline: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during pipeline setup: {str(e)}")
            raise SearchSetupError(f"Pipeline setup failed: {str(e)}")

    def check_pipeline_status(self) -> Dict[str, Any]:
        """Check the status of the integrated vectorization pipeline."""
        logger.info("Checking pipeline status...")
        
        try:
            # Get indexer status
            status = self.get_indexer_status("ix-spofiles-integrated")
            
            logger.info(f"Indexer status: {status.get('status', 'unknown')}")
            
            if "lastResult" in status:
                last_result = status["lastResult"]
                logger.info(f"Last execution: {last_result.get('status', 'unknown')}")
                logger.info(f"Items processed: {last_result.get('itemsProcessed', 0)}")
                logger.info(f"Items failed: {last_result.get('itemsFailed', 0)}")
                
                if last_result.get("errors"):
                    logger.warning("Errors found:")
                    for error in last_result["errors"][:5]:  # Show first 5 errors
                        logger.warning(f"  - {error.get('errorMessage', 'Unknown error')}")
            
            return status
            
        except SearchSetupError as e:
            logger.error(f"Failed to check pipeline status: {str(e)}")
            raise