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

class AzureSearchSetup:
    """Handles Azure AI Search configuration and setup."""
    
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
            if response.status_code in [200, 201, 204]:
                try:
                    return response.json() if response.content else {}
                except ValueError:
                    return {}
            elif response.status_code == 404:
                return {"error": "Resource not found", "status_code": 404}
            else:
                response.raise_for_status()
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    logger.error(f"Error details: {error_detail}")
                except ValueError:
                    logger.error(f"Response text: {e.response.text}")
            raise SearchSetupError(f"API request failed: {e}")
    
    def create_data_source(self, name: str = "ds-spofiles") -> Dict[str, Any]:
        """Create Azure Blob data source for the search service."""
        logger.info(f"Creating data source: {name}")
        
        data_source_definition = {
            "name": name,
            "type": "azureblob",
            "credentials": {
                "connectionString": f"ResourceId=/subscriptions/{{subscription-id}}/resourceGroups/{{resource-group}}/providers/Microsoft.Storage/storageAccounts/{self.config.storage_account_name};"
            },
            "container": {
                "name": self.config.az_container
            },
            "description": "SharePoint files synced to Azure Blob Storage (Service Principal auth)"
        }
        
        result = self._make_request("POST", "datasources", data_source_definition)
        
        if "error" in result:
            if result.get("status_code") == 404:
                logger.error("Search service not found. Check your search endpoint and API key.")
            raise SearchSetupError(f"Failed to create data source: {result}")
        
        logger.info(f"Successfully created data source: {name}")
        return result
    
    def create_skillset(self, name: str = "ss-spofiles") -> Dict[str, Any]:
        """Create skillset for document processing with embeddings."""
        logger.info(f"Creating skillset: {name}")
        
        skills = [
            {
                "@odata.type": "#Microsoft.Skills.Text.EntityRecognitionSkill",
                "name": "entities",
                "description": "Extract entities from content",
                "context": "/document",
                "categories": ["Person", "Location", "Organization"],
                "inputs": [
                    {"name": "text", "source": "/document/content"}
                ],
                "outputs": [
                    {"name": "entities", "targetName": "entities"}
                ]
            },
            {
                "@odata.type": "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill",
                "name": "embeddings",
                "description": "Generate embeddings for content",
                "context": "/document",
                "resourceUri": self.config.azure_openai_endpoint,
                "apiKey": self.config.azure_openai_api_key,
                "deploymentId": self.config.azure_openai_embedding_model,
                "inputs": [
                    {"name": "text", "source": "/document/content"}
                ],
                "outputs": [
                    {"name": "embedding", "targetName": "contentVector"}
                ]
            }
        ]
        
        logger.info("Added Azure OpenAI embedding skill to skillset")
        
        skillset_definition = {
            "name": name,
            "description": "Skillset for processing SharePoint documents",
            "skills": skills
        }
        
        result = self._make_request("POST", "skillsets", skillset_definition)
        
        if "error" in result:
            raise SearchSetupError(f"Failed to create skillset: {result}")
        
        logger.info(f"Successfully created skillset: {name}")
        return result
    
    def create_index(self, name: str = "idx-spofiles") -> Dict[str, Any]:
        """Create search index with vector field for embeddings."""
        logger.info(f"Creating index: {name}")
        
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
                "name": "entities",
                "type": "Collection(Edm.String)",
                "searchable": True,
                "filterable": True,
                "retrievable": True
            },
            {
                "name": "contentVector",
                "type": "Collection(Edm.Single)",
                "searchable": True,
                "retrievable": False,
                "vectorSearchDimensions": 1536,  # text-embedding-3-small dimensions
                "vectorSearchProfileName": "vector-profile"
            }
        ]
        
        index_definition = {
            "name": name,
            "fields": fields,
            "vectorSearch": {
                "algorithms": [
                    {
                        "name": "hnsw-algorithm",
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
                        "name": "vector-profile",
                        "algorithm": "hnsw-algorithm"
                    }
                ]
            }
        }
        
        result = self._make_request("POST", "indexes", index_definition)
        
        if "error" in result:
            raise SearchSetupError(f"Failed to create index: {result}")
        
        logger.info(f"Successfully created index: {name}")
        return result
    
    def create_indexer(self, name: str = "ix-spofiles", 
                      data_source_name: str = "ds-spofiles",
                      index_name: str = "idx-spofiles", 
                      skillset_name: str = "ss-spofiles") -> Dict[str, Any]:
        """Create indexer to process documents."""
        logger.info(f"Creating indexer: {name}")
        
        indexer_definition = {
            "name": name,
            "dataSourceName": data_source_name,
            "targetIndexName": index_name,
            "skillsetName": skillset_name,
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
                    "sourceFieldName": "metadata_source_url",
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
            ],
            "outputFieldMappings": [
                {
                    "sourceFieldName": "/document/entities",
                    "targetFieldName": "entities"
                },
                {
                    "sourceFieldName": "/document/contentVector",
                    "targetFieldName": "contentVector"
                }
            ],
            "schedule": {
                "interval": "PT30M"  # Every 30 minutes
            }
        }
        
        result = self._make_request("POST", "indexers", indexer_definition)
        
        if "error" in result:
            raise SearchSetupError(f"Failed to create indexer: {result}")
        
        logger.info(f"Successfully created indexer: {name}")
        return result
    
    def run_indexer(self, name: str = "ix-spofiles") -> Dict[str, Any]:
        """Run the indexer to process documents."""
        logger.info(f"Running indexer: {name}")
        
        result = self._make_request("POST", f"indexers/{name}/run")
        
        if "error" in result:
            raise SearchSetupError(f"Failed to run indexer: {result}")
        
        logger.info(f"Successfully started indexer: {name}")
        return result
    
    def get_indexer_status(self, name: str = "ix-spofiles") -> Dict[str, Any]:
        """Get indexer status and execution history."""
        logger.info(f"Getting indexer status: {name}")
        
        result = self._make_request("GET", f"indexers/{name}/status")
        
        if "error" in result:
            raise SearchSetupError(f"Failed to get indexer status: {result}")
        
        return result
    
    def list_resources(self) -> Dict[str, List[str]]:
        """List all search service resources."""
        logger.info("Listing search service resources...")
        
        resources = {
            "datasources": [],
            "indexes": [],
            "skillsets": [],
            "indexers": []
        }
        
        for resource_type in resources.keys():
            try:
                result = self._make_request("GET", resource_type)
                if "value" in result:
                    resources[resource_type] = [item["name"] for item in result["value"]]
                elif isinstance(result, list):
                    resources[resource_type] = [item["name"] for item in result]
            except Exception as e:
                logger.warning(f"Failed to list {resource_type}: {e}")
        
        return resources
    
    def delete_resource(self, resource_type: str, name: str) -> bool:
        """Delete a search service resource."""
        logger.info(f"Deleting {resource_type}: {name}")
        
        try:
            result = self._make_request("DELETE", f"{resource_type}/{name}")
            logger.info(f"Successfully deleted {resource_type}: {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete {resource_type} {name}: {e}")
            return False
    
    def setup_complete_pipeline(self) -> Dict[str, Any]:
        """Set up the complete search pipeline with vector embeddings."""
        logger.info("Setting up complete Azure AI Search pipeline with vector embeddings...")
        
        results = {}
        
        try:
            # Create data source
            results["datasource"] = self.create_data_source()
            
            # Create skillset with embeddings
            results["skillset"] = self.create_skillset()
            
            # Create index with vector field
            results["index"] = self.create_index()
            
            # Create indexer
            results["indexer"] = self.create_indexer()
            
            logger.info("Successfully set up complete Azure AI Search pipeline with vector embeddings!")
            
        except Exception as e:
            logger.error(f"Failed to set up complete pipeline: {e}")
            results["error"] = str(e)
        
        return results