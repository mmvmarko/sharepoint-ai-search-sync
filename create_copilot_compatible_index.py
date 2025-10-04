import json
import requests
from config.settings import config

def create_copilot_studio_compatible_index():
    """Create a simple, reliable index that works with Copilot Studio without vectors."""
    
    headers = {
        "Content-Type": "application/json",
        "api-key": config.search_api_key
    }
    
    print("🚀 Creating Copilot Studio Compatible Index (Text-Only)")
    print("=" * 60)
    
    # Simple, reliable index without vectors
    index_definition = {
        "name": "idx-spofiles-copilot",
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
                "filterable": True,
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
            }
        ]
        # No vector search configuration - pure text search
    }
    
    print("1️⃣ Creating simple text-based index...")
    create_url = f"{config.search_endpoint}/indexes/idx-spofiles-copilot?api-version=2024-07-01"
    
    try:
        response = requests.put(create_url, headers=headers, json=index_definition)
        
        if response.status_code in [200, 201]:
            print("✅ Index created successfully!")
        else:
            print(f"❌ Failed to create index: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error creating index: {e}")
        return False
    
    # Create simple indexer
    print("\n2️⃣ Creating indexer...")
    
    indexer_definition = {
        "name": "ix-spofiles-copilot",
        "dataSourceName": "ds-spofiles-integrated",  # Reuse existing data source
        "targetIndexName": "idx-spofiles-copilot",
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
    
    indexer_url = f"{config.search_endpoint}/indexers/ix-spofiles-copilot?api-version=2024-07-01"
    
    try:
        response = requests.put(indexer_url, headers=headers, json=indexer_definition)
        
        if response.status_code in [200, 201]:
            print("✅ Indexer created successfully!")
        else:
            print(f"❌ Failed to create indexer: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error creating indexer: {e}")
        return False
    
    # Run indexer
    print("\n3️⃣ Running indexer...")
    
    run_url = f"{config.search_endpoint}/indexers/ix-spofiles-copilot/run?api-version=2024-07-01"
    try:
        response = requests.post(run_url, headers=headers)
        if response.status_code in [200, 202]:
            print("✅ Indexer started")
            
            print("\n🎉 Copilot Studio Compatible Index Created!")
            print("\n📋 What was created:")
            print("   • Index: idx-spofiles-copilot (text-based, no vectors)")
            print("   • Indexer: ix-spofiles-copilot")
            print("   • Full text search capabilities")
            print("   • Compatible with Copilot Studio")
            
            print("\n📖 Next steps:")
            print("1. Wait 2-3 minutes for indexing to complete")
            print("2. Test: python test_search_functionality.py (edit to use new index)")
            print("3. Use 'idx-spofiles-copilot' in Copilot Studio")
            print("4. This will work reliably without vector issues!")
            
            return True
        else:
            print(f"❌ Failed to run indexer: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error running indexer: {e}")
        return False

if __name__ == "__main__":
    success = create_copilot_studio_compatible_index()
    if success:
        print("\n✅ Copilot Studio compatible index setup completed!")
        print("\n💡 This text-based index will work reliably with Copilot Studio")
        print("   even though it doesn't use vectors. Modern search is very effective!")
    else:
        print("\n❌ Setup failed. Check the errors above.")