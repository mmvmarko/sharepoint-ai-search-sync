import json
import requests
from config.settings import config

def check_actual_vector_data():
    """Check if documents actually have vector embeddings stored."""
    
    headers = {
        "Content-Type": "application/json",
        "api-key": config.search_api_key
    }
    
    print("🔍 Checking for Actual Vector Data in Documents")
    print("=" * 60)
    
    # Try to get documents with vector field included
    search_url = f"{config.search_endpoint}/indexes/idx-spofiles-integrated/docs/search?api-version=2024-07-01"
    
    # Get a few documents and check if they have vector data
    search_payload = {
        "search": "*",
        "select": "id,title,content_vector",
        "top": 3
    }
    
    try:
        response = requests.post(search_url, headers=headers, json=search_payload)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('value'):
                print(f"📄 Checking {len(result['value'])} documents for vector data:")
                
                for i, doc in enumerate(result['value'], 1):
                    title = doc.get('title', 'No title')
                    vector_data = doc.get('content_vector')
                    
                    print(f"\n  {i}. Document: {title}")
                    
                    if vector_data is None:
                        print(f"     Vector: ❌ NULL (no embedding generated)")
                    elif isinstance(vector_data, list) and len(vector_data) > 0:
                        print(f"     Vector: ✅ Present ({len(vector_data)} dimensions)")
                        # Check if it's all zeros (another common issue)
                        if all(v == 0.0 for v in vector_data[:10]):  # Check first 10 values
                            print(f"     Warning: ⚠️  Vector appears to be all zeros")
                        else:
                            print(f"     Sample values: {vector_data[:3]}... (looks good)")
                    elif isinstance(vector_data, list) and len(vector_data) == 0:
                        print(f"     Vector: ❌ Empty array")
                    else:
                        print(f"     Vector: ❌ Unexpected format: {type(vector_data)}")
            else:
                print("❌ No documents found")
                
        else:
            print(f"❌ Search failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def test_azure_openai_connection():
    """Test if Azure OpenAI endpoint is accessible."""
    
    print(f"\n🧪 Testing Azure OpenAI Connection")
    print("=" * 60)
    
    # Test the embedding endpoint directly
    embedding_url = f"{config.azure_openai_endpoint}/openai/deployments/{config.azure_openai_embedding_model}/embeddings?api-version=2023-05-15"
    
    headers = {
        "Content-Type": "application/json",
        "api-key": config.azure_openai_api_key
    }
    
    test_payload = {
        "input": "test document content"
    }
    
    try:
        response = requests.post(embedding_url, headers=headers, json=test_payload)
        
        if response.status_code == 200:
            result = response.json()
            if 'data' in result and result['data']:
                embedding = result['data'][0].get('embedding', [])
                print(f"✅ Azure OpenAI connection successful!")
                print(f"📊 Embedding dimensions: {len(embedding)}")
                print(f"🔢 Sample values: {embedding[:3]}...")
            else:
                print(f"❌ Unexpected response format: {result}")
        else:
            print(f"❌ Azure OpenAI connection failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error testing OpenAI: {e}")

def suggest_fix():
    """Suggest how to fix the integrated vectorization issue."""
    
    print(f"\n💡 Potential Solutions")
    print("=" * 60)
    
    print("🔧 Based on the diagnosis, try these solutions:")
    print()
    
    print("1️⃣ **Recreate Index with Proper Vector Configuration**")
    print("   • The current index might have been created incorrectly")
    print("   • Delete and recreate with proper integrated vectorization")
    print()
    
    print("2️⃣ **Check Azure OpenAI Model Deployment**")
    print("   • Ensure 'text-embedding-3-small' is deployed")
    print("   • Verify deployment name matches exactly")
    print()
    
    print("3️⃣ **Use Alternative: Skillset-Based Approach**")
    print("   • Your previous idx-spofiles-v2 with skillsets might work better")
    print("   • Skillsets are more reliable than integrated vectorization")
    print()
    
    print("4️⃣ **Force Indexer Reset and Rerun**")
    print("   • Reset the indexer to force re-processing")
    print("   • This might fix vector generation issues")

if __name__ == "__main__":
    check_actual_vector_data()
    test_azure_openai_connection()
    suggest_fix()