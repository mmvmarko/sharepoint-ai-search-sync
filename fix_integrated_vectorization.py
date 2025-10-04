import json
import requests
from config.settings import config

def fix_integrated_vectorization():
    """Fix the integrated vectorization index by recreating it properly."""
    
    headers = {
        "Content-Type": "application/json",
        "api-key": config.search_api_key
    }
    
    print("🔧 Fixing Integrated Vectorization Index")
    print("=" * 60)
    
    # Step 1: Delete the problematic index
    print("1️⃣ Deleting current index...")
    delete_url = f"{config.search_endpoint}/indexes/idx-spofiles-integrated?api-version=2024-07-01"
    
    try:
        response = requests.delete(delete_url, headers=headers)
        if response.status_code in [200, 204, 404]:  # 404 is OK if it doesn't exist
            print("✅ Index deleted (or didn't exist)")
        else:
            print(f"⚠️  Delete response: {response.status_code}")
    except Exception as e:
        print(f"⚠️  Delete error (continuing anyway): {e}")
    
    # Step 2: Create corrected index with retrievable vector field
    print("\n2️⃣ Creating corrected index...")
    
    corrected_index_definition = {
        "name": "idx-spofiles-integrated",
        "fields": [
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
                "retrievable": True,  # FIXED: Made retrievable
                "dimensions": 1536,
                "vectorSearchProfile": "default-vector-profile"
            }
        ],
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
                        "resourceUri": config.azure_openai_endpoint,
                        "deploymentId": config.azure_openai_embedding_model,
                        "apiKey": config.azure_openai_api_key,
                        "modelName": "text-embedding-3-small"
                    }
                }
            ]
        }
    }
    
    create_url = f"{config.search_endpoint}/indexes/idx-spofiles-integrated?api-version=2024-07-01"
    
    try:
        response = requests.put(create_url, headers=headers, json=corrected_index_definition)
        
        if response.status_code in [200, 201]:
            print("✅ Corrected index created successfully!")
        else:
            print(f"❌ Failed to create index: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error creating index: {e}")
        return False
    
    # Step 3: Reset and run the indexer
    print("\n3️⃣ Resetting and running indexer...")
    
    # Reset indexer
    reset_url = f"{config.search_endpoint}/indexers/ix-spofiles-integrated/reset?api-version=2024-07-01"
    try:
        response = requests.post(reset_url, headers=headers)
        if response.status_code in [200, 204]:
            print("✅ Indexer reset")
        else:
            print(f"⚠️  Reset response: {response.status_code}")
    except Exception as e:
        print(f"⚠️  Reset error: {e}")
    
    # Run indexer
    run_url = f"{config.search_endpoint}/indexers/ix-spofiles-integrated/run?api-version=2024-07-01"
    try:
        response = requests.post(run_url, headers=headers)
        if response.status_code in [200, 202]:
            print("✅ Indexer started")
            print("\n🎉 Fix completed! Wait a few minutes then test the index.")
            print("\n📖 Next steps:")
            print("1. Wait 2-3 minutes for indexing to complete")
            print("2. Run: python main.py check-integrated-status")
            print("3. Test search functionality")
            print("4. Use in Copilot Studio")
            return True
        else:
            print(f"❌ Failed to run indexer: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error running indexer: {e}")
        return False

if __name__ == "__main__":
    success = fix_integrated_vectorization()
    if success:
        print("\n✅ All steps completed successfully!")
    else:
        print("\n❌ Some steps failed. Check the errors above.")