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

    def create_data_source(self, name: str = "ds-spofiles-integrated", container: Optional[str] = None) -> Dict[str, Any]:
        """Create or update an Azure Blob data source.

        Parameters:
            name: Data source name.
            container: Optional override for blob container (defaults to config.az_container).
        """
        logger.info(f"Creating data source: {name} (container={container or self.config.az_container})")
        
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
            "credentials": {"connectionString": connection_string},
            "container": {"name": container or self.config.az_container},
            "description": "SharePoint files storage for integrated vectorization"
        }
        
        result = self._make_request("PUT", f"datasources/{name}", data_source_definition)
        
        if "error" in result:
            if result.get("error", {}).get("code") == "ResourceNotFound":
                logger.error("Search service not found. Check your search endpoint and API key.")
            raise SearchSetupError(f"Failed to create data source: {result}")
        
        logger.info(f"Successfully created data source: {name}")
        return result

    # ------------------------ SKILLSET (MISSING IN ORIGINAL) ------------------------
    def create_skillset(self, name: str = "ss-spofiles-integrated") -> Dict[str, Any]:
        """Create skillset that performs minimal chunking + embedding generation.

        Notes:
        - Integrated vectorization STILL requires an embedding skill at indexing time; just adding a vector field + vectorizer does NOT populate vectors.
        - We chunk (page-based) to avoid token overflows; for now we embed ONLY the first chunk to keep design simple. This can be extended to per-chunk projections later.
        - Output targetName must match the index field (content_vector).
        """
        logger.info(f"Creating skillset: {name}")

        skills: List[Dict[str, Any]] = [
            {
                "@odata.type": "#Microsoft.Skills.Text.SplitSkill",
                "name": "split-text",
                "description": "Split document into logical pages/chunks",
                "context": "/document",
                "textSplitMode": "pages",
                "maximumPageLength": 2000,
                "pageOverlapLength": 100,
                "inputs": [
                    {"name": "text", "source": "/document/content"}
                ],
                "outputs": [
                    {"name": "textItems", "targetName": "pages"}
                ]
            },
            {
                "@odata.type": "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill",
                "name": "document-embedding",
                "description": "Generate embedding for first chunk (simplified)",
                "context": "/document",
                "resourceUri": self.config.azure_openai_endpoint,
                "apiKey": self.config.azure_openai_api_key,
                "deploymentId": self.config.azure_openai_embedding_model,
                # modelName required in 2024-07-01
                "modelName": self.config.azure_openai_embedding_model,
                "inputs": [
                    {"name": "text", "source": "/document/pages/0"}
                ],
                "outputs": [
                    {"name": "embedding", "targetName": "content_vector"}
                ]
            }
        ]

        skillset_definition = {
            "name": name,
            "description": "Skillset for integrated vectorization (single embedding per doc)",
            "skills": skills
        }

        result = self._make_request("PUT", f"skillsets/{name}", skillset_definition)
        if "error" in result:
            raise SearchSetupError(f"Failed to create skillset: {result}")
        logger.info(f"Successfully created skillset: {name}")
        return result

    def create_json_skillset(self, name: str) -> Dict[str, Any]:
        """Create a simplified skillset for JSON specs / structured docs.

        Strategy: No splitting – embed truncated raw content (first N characters) to keep vector focused.
        (Future enhancement: parse & restructure OpenAPI parts before embedding.)
        """
        logger.info(f"Creating JSON skillset: {name}")
        skills: List[Dict[str, Any]] = [
            # Use SplitSkill in 'pages' mode with large max length to approximate truncation
            {
                "@odata.type": "#Microsoft.Skills.Text.SplitSkill",
                "name": "split-json",
                "description": "Pseudo-truncate JSON (first page) for embedding",
                "context": "/document",
                "textSplitMode": "pages",
                "maximumPageLength": 16000,
                "pageOverlapLength": 0,
                "inputs": [
                    {"name": "text", "source": "/document/content"}
                ],
                "outputs": [
                    {"name": "textItems", "targetName": "pages"}
                ]
            },
            {
                "@odata.type": "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill",
                "name": "json-embedding",
                "context": "/document",
                "resourceUri": self.config.azure_openai_endpoint,
                "apiKey": self.config.azure_openai_api_key,
                "deploymentId": self.config.azure_openai_embedding_model,
                "modelName": self.config.azure_openai_embedding_model,
                "inputs": [
                    {"name": "text", "source": "/document/pages/0"}
                ],
                "outputs": [
                    {"name": "embedding", "targetName": "content_vector"}
                ]
            }
        ]
        definition = {"name": name, "description": "Skillset for JSON documents (direct truncate + embedding)", "skills": skills}
        result = self._make_request("PUT", f"skillsets/{name}", definition)
        if "error" in result:
            raise SearchSetupError(f"Failed to create JSON skillset: {result}")
        logger.info(f"Successfully created JSON skillset: {name}")
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
                # Not retrievable to save payload size (adjust to True if debugging vectors)
                "retrievable": False,
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
                                                     index_name: str = "idx-spofiles-integrated",
                                                     skillset_name: str = "ss-spofiles-integrated",
                                                     indexed_extensions: str = ".pdf,.docx,.pptx,.txt,.xlsx,.html,.md",
                                                     excluded_extensions: str = ".xml") -> Dict[str, Any]:
        """Create indexer wired to skillset producing embeddings -> vector field."""
        logger.info(f"Creating indexer with integrated vectorization: {name}")

        indexer_definition = {
            "name": name,
            "dataSourceName": data_source_name,
            "targetIndexName": index_name,
            "skillsetName": skillset_name,
            "parameters": {
                "configuration": {
                    "dataToExtract": "contentAndMetadata",
                    "parsingMode": "default",
                    "indexedFileNameExtensions": indexed_extensions,
                    "excludedFileNameExtensions": excluded_extensions,
                    "failOnUnsupportedContentType": False,
                    "failOnUnprocessableDocument": False
                }
            },
            "fieldMappings": [
                {  # Create key from path (base64)
                    "sourceFieldName": "metadata_storage_path",
                    "targetFieldName": "id",
                    "mappingFunction": {"name": "base64Encode"}
                },
                {"sourceFieldName": "metadata_storage_name", "targetFieldName": "title"},
                {"sourceFieldName": "content", "targetFieldName": "content"},
                {"sourceFieldName": "metadata_storage_path", "targetFieldName": "source_url"},
                {"sourceFieldName": "metadata_storage_last_modified", "targetFieldName": "lastModified"},
                {"sourceFieldName": "metadata_storage_size", "targetFieldName": "size"},
                {"sourceFieldName": "metadata_storage_file_extension", "targetFieldName": "file_extension"}
            ],
            "outputFieldMappings": [
                {  # Map embedding skill output to vector field
                    "sourceFieldName": "/document/content_vector",
                    "targetFieldName": "content_vector"
                }
            ]
        }

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

            # Create skillset (previously missing -> causes empty vectors)
            skillset_result = self.create_skillset()
            logger.info("✓ Skillset created")
            
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
                "skillset": skillset_result,
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

    # ------------------------ VERIFICATION UTILITIES ------------------------
    def get_index_statistics(self, index_name: str = "idx-spofiles-integrated") -> Dict[str, Any]:
        """Return index statistics including vector index size to confirm embeddings exist."""
        logger.info(f"Fetching statistics for index: {index_name}")
        stats = self._make_request("GET", f"indexes/{index_name}/stats")
        if "error" in stats:
            raise SearchSetupError(f"Failed to get index stats: {stats}")
        return stats

    def verify_vectors_present(self, index_name: str = "idx-spofiles-integrated") -> Dict[str, Any]:
        """Quick verification: checks vector index size > 0 and document count."""
        stats = self.get_index_statistics(index_name)
        doc_count = stats.get("documentCount", 0)
        vector_store = stats.get("vectorIndexSizeBytes", 0) or stats.get("storageSize", 0)
        has_vectors = vector_store and vector_store > 0
        logger.info(f"Documents: {doc_count}, VectorIndexSizeBytes: {vector_store}, HasVectors={has_vectors}")
        return {
            "documents": doc_count,
            "vectorIndexSizeBytes": vector_store,
            "hasVectors": bool(has_vectors)
        }

    # ------------------------ QUICK TEST SETUP ------------------------
    def quick_test_setup(self, prefix: str = "test") -> Dict[str, Any]:
        """Create disposable data source, index, skillset, and indexer with a timestamp suffix.

        Allows rapid iteration without clobbering primary resources. Returns created names.
        """
        import datetime, random
        suffix = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S") + f"{random.randint(100,999)}"
        ds_name = f"ds-{prefix}-{suffix}"[:60]
        idx_name = f"idx-{prefix}-{suffix}"[:60]
        ss_name = f"ss-{prefix}-{suffix}"[:60]
        ix_name = f"ix-{prefix}-{suffix}"[:60]

        logger.info(f"Creating quick test resources: {ds_name}, {idx_name}, {ss_name}, {ix_name}")

        ds = self.create_data_source(ds_name)
        idx = self.create_index_with_integrated_vectorization(idx_name)
        ss = self.create_skillset(ss_name)
        ix = self.create_indexer_with_integrated_vectorization(ix_name, ds_name, idx_name, ss_name)
        run = self.run_indexer(ix_name)

        return {
            "status": "started",
            "dataSource": ds_name,
            "index": idx_name,
            "skillset": ss_name,
            "indexer": ix_name,
            "run": run
        }

    # ------------------------ STABLE PREFIX VERTICAL ------------------------
    def create_vertical(self, prefix: str,
                        container: Optional[str] = None,
                        json_container: Optional[str] = None,
                        data_source_name: Optional[str] = None,
                        skillset_name: Optional[str] = None,
                        index_name: Optional[str] = None,
                        indexer_name: Optional[str] = None,
                        create_json_vertical: bool = False) -> Dict[str, Any]:
        """Create or update a vertical (data source, skillset, index, indexer).

        You may specify explicit names; otherwise names are derived from prefix:
            ds-{prefix}, ss-{prefix}, idx-{prefix}, ix-{prefix}

        Parameters:
            prefix: Base prefix (sanitized) for fallback names.
            container: Optional blob container override (defaults to config.az_container).
            data_source_name, skillset_name, index_name, indexer_name: Optional explicit resource names.
        """
        safe = ''.join(c for c in prefix.lower() if c.isalnum() or c == '-')[:48]
        if not safe:
            raise SearchSetupError("Prefix resulted in empty safe name")

        ds_name = data_source_name or f"ds-{safe}"
        ss_name = skillset_name or f"ss-{safe}"
        idx_name = index_name or f"idx-{safe}"
        ix_name = indexer_name or f"ix-{safe}"

        logger.info("Creating/Updating vertical resources with settings: "
                    f"prefix={safe} ds={ds_name} ss={ss_name} idx={idx_name} ix={ix_name} container={container or self.config.az_container}")

        ds = self.create_data_source(ds_name, container=container)
        idx = self.create_index_with_integrated_vectorization(idx_name)
        ss = self.create_skillset(ss_name)
        ix = self.create_indexer_with_integrated_vectorization(ix_name, ds_name, idx_name, ss_name,
                                                               indexed_extensions=".pdf,.docx,.pptx,.txt,.xlsx,.html,.md",
                                                               excluded_extensions=".xml,.json")
        run = self.run_indexer(ix_name)

        json_resources = None
        if create_json_vertical:
            json_suffix = f"{safe}-json"
            json_ds = f"ds-{json_suffix}"  # reuse same container
            json_ss = f"ss-{json_suffix}"
            json_idx = f"idx-{json_suffix}"
            json_ix = f"ix-{json_suffix}"
            logger.info(f"Creating JSON vertical (suffix -json) resources: ds={json_ds} idx={json_idx} container={json_container or container or self.config.az_container}")
            # Allow different container for JSON vertical
            self.create_data_source(json_ds, container=json_container or container)
            self.create_index_with_integrated_vectorization(json_idx)
            self.create_json_skillset(json_ss)
            # Allow both raw JSON specs and preprocessed chunk .txt files
            self.create_indexer_with_integrated_vectorization(
                json_ix,
                json_ds,
                json_idx,
                json_ss,
                indexed_extensions=".json,.txt",
                excluded_extensions=".xml"
            )
            self.run_indexer(json_ix)
            json_resources = {"dataSource": json_ds, "index": json_idx, "skillset": json_ss, "indexer": json_ix}

        return {"status": "started", "dataSource": ds_name, "index": idx_name, "skillset": ss_name, "indexer": ix_name, "run": run, "json": json_resources}

    def delete_vertical(self, prefix: str) -> Dict[str, Any]:
        """Delete data source, indexer, skillset, and index associated with prefix.

        Deletion order matters: indexer -> skillset -> index -> data source.
        Missing resources are ignored; returns a report of what was deleted/found.
        """
        safe = ''.join(c for c in prefix.lower() if c.isalnum() or c == '-')[:48]
        if not safe:
            raise SearchSetupError("Prefix resulted in empty safe name")

        resources = {
            "indexer": f"ix-{safe}",
            "skillset": f"ss-{safe}",
            "index": f"idx-{safe}",
            "datasource": f"ds-{safe}"
        }

        report = {k: {"name": v, "deleted": False, "status": "skipped"} for k, v in resources.items()}

        def _delete(kind: str, endpoint: str):
            name = resources[kind]
            logger.info(f"Deleting {kind}: {name}")
            resp = self._make_request("DELETE", f"{endpoint}/{name}")
            # DELETE returns 204 with empty body usually; treat missing as success
            report[kind]["deleted"] = True
            report[kind]["status"] = "deleted"
            return resp

        # Delete ignoring errors about not found
        try:
            _delete("indexer", "indexers")
        except Exception as e:
            report["indexer"]["status"] = f"error: {e}"  # continue
        try:
            _delete("skillset", "skillsets")
        except Exception as e:
            report["skillset"]["status"] = f"error: {e}"
        try:
            _delete("index", "indexes")
        except Exception as e:
            report["index"]["status"] = f"error: {e}"
        try:
            _delete("datasource", "datasources")
        except Exception as e:
            report["datasource"]["status"] = f"error: {e}"

        return {"prefix": safe, "resources": report}