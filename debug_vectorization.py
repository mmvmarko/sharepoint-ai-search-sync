import json
import requests
from config.settings import config

def debug_integrated_vectorization():
    """Debug the integrated vectorization index configuration."""
    
    headers = {
        "Content-Type": "application/json",
        "api-key": config.search_api_key
    }
    
    print("🔍 Debugging Integrated Vectorization Index")
    print("=" * 60)
    
    # Check the index definition in detail
    index_url = f"{config.search_endpoint}/indexes/idx-spofiles-integrated?api-version=2024-07-01"
    
    try:
        response = requests.get(index_url, headers=headers)
        
        if response.status_code == 200:
            index_def = response.json()
            
            print("✅ Index exists")
            print(f"📋 Index name: {index_def.get('name')}")
            
            # Check vector search configuration
            vector_search = index_def.get('vectorSearch', {})
            print(f"\n🔍 Vector Search Configuration:")
            
            if not vector_search:
                print("❌ No vector search configuration found!")
                return
            
            # Check vectorizers
            vectorizers = vector_search.get('vectorizers', [])
            print(f"📡 Vectorizers ({len(vectorizers)}):")
            for vectorizer in vectorizers:
                print(f"  • Name: {vectorizer.get('name')}")
                print(f"    Kind: {vectorizer.get('kind')}")
                if vectorizer.get('kind') == 'azureOpenAI':
                    params = vectorizer.get('azureOpenAIParameters', {})
                    print(f"    Resource URI: {params.get('resourceUri', 'Not set')}")
                    print(f"    Deployment ID: {params.get('deploymentId', 'Not set')}")
                    print(f"    Model: {params.get('modelName', 'Not set')}")
                    # Don't print API key for security
                    has_key = bool(params.get('apiKey'))
                    print(f"    API Key: {'Set' if has_key else 'Not set'}")
                print()
            
            # Check vector fields
            fields = index_def.get('fields', [])
            vector_fields = [f for f in fields if 'Collection(Edm.Single)' in f.get('type', '')]
            print(f"🔢 Vector Fields ({len(vector_fields)}):")
            for field in vector_fields:
                print(f"  • {field.get('name')}: {field.get('type')}")
                print(f"    Dimensions: {field.get('dimensions', 'Not set')}")
                print(f"    Vector Profile: {field.get('vectorSearchProfile', 'Not set')}")
                print()
            
            # Check if there are any issues with the configuration
            profiles = vector_search.get('profiles', [])
            print(f"📊 Vector Profiles ({len(profiles)}):")
            for profile in profiles:
                print(f"  • Name: {profile.get('name')}")
                print(f"    Algorithm: {profile.get('algorithm')}")
                print(f"    Vectorizer: {profile.get('vectorizer')}")
                print()
                
        else:
            print(f"❌ Failed to get index: {response.status_code}")
            print(f"Response: {response.text}")
    
    except Exception as e:
        print(f"❌ Error: {e}")

def test_direct_vector_search():
    """Test vector search directly to see what happens."""
    
    headers = {
        "Content-Type": "application/json",
        "api-key": config.search_api_key
    }
    
    print(f"\n🧪 Testing Direct Vector Search")
    print("=" * 60)
    
    search_url = f"{config.search_endpoint}/indexes/idx-spofiles-integrated/docs/search?api-version=2024-07-01"
    
    # Test vector search with text-to-vector conversion
    vector_search_payload = {
        "vectorQueries": [
            {
                "kind": "text",
                "text": "user manual documentation",
                "fields": "content_vector",
                "k": 5
            }
        ],
        "select": "id,title,content",
        "top": 5
    }
    
    try:
        print("Testing vector search with text-to-vector conversion...")
        response = requests.post(search_url, headers=headers, json=vector_search_payload)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Vector search successful!")
            print(f"📊 Found {len(result.get('value', []))} results")
            
            if result.get('value'):
                for i, doc in enumerate(result['value'], 1):
                    score = doc.get('@search.score', 'No score')
                    print(f"  {i}. {doc.get('title', 'No title')} (Score: {score})")
            else:
                print("⚠️  No results found")
        else:
            print(f"❌ Vector search failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def check_indexer_vector_processing():
    """Check if the indexer is properly processing vectors."""
    
    headers = {
        "Content-Type": "application/json",
        "api-key": config.search_api_key
    }
    
    print(f"\n🔄 Checking Indexer Vector Processing")
    print("=" * 60)
    
    # Get indexer status with detailed info
    status_url = f"{config.search_endpoint}/indexers/ix-spofiles-integrated/status?api-version=2024-07-01"
    
    try:
        response = requests.get(status_url, headers=headers)
        
        if response.status_code == 200:
            status = response.json()
            
            print(f"📊 Indexer Status: {status.get('status')}")
            
            # Check latest execution
            if 'lastResult' in status:
                last_result = status['lastResult']
                print(f"📅 Last execution: {last_result.get('status')}")
                print(f"📈 Items processed: {last_result.get('itemsProcessed', 0)}")
                print(f"❌ Items failed: {last_result.get('itemsFailed', 0)}")
                
                # Check for vector-related errors
                if last_result.get('errors'):
                    print(f"\n⚠️  Errors found:")
                    for error in last_result['errors'][:3]:
                        message = error.get('errorMessage', 'Unknown error')
                        print(f"  • {message}")
                        
                        # Look for vector-specific errors
                        if any(keyword in message.lower() for keyword in ['vector', 'embedding', 'openai', 'dimension']):
                            print(f"    ^ This might be vector-related!")
                
                if last_result.get('warnings'):
                    print(f"\n⚠️  Warnings found:")
                    for warning in last_result['warnings'][:3]:
                        message = warning.get('message', 'Unknown warning')
                        print(f"  • {message}")
            
        else:
            print(f"❌ Failed to get indexer status: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_integrated_vectorization()
    test_direct_vector_search()
    check_indexer_vector_processing()