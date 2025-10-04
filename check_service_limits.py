import json
import requests
from config.settings import config

def check_search_service_limits():
    """Check Azure AI Search service limits and quotas."""
    
    headers = {
        "Content-Type": "application/json",
        "api-key": config.search_api_key
    }
    
    print("🔍 Checking Azure AI Search Service Limits and Quotas")
    print("=" * 60)
    
    # Get service statistics
    stats_url = f"{config.search_endpoint}/servicestats?api-version=2024-07-01"
    
    try:
        response = requests.get(stats_url, headers=headers)
        
        if response.status_code == 200:
            stats = response.json()
            
            print("📊 Service Statistics:")
            print(f"  • Storage Used: {stats.get('storageSize', 'unknown')} bytes")
            print(f"  • Document Count: {stats.get('documentCount', 'unknown')}")
            print(f"  • Index Count: {stats.get('indexCount', 'unknown')}")
            print(f"  • Indexer Count: {stats.get('indexerCount', 'unknown')}")
            print(f"  • Data Source Count: {stats.get('dataSourceCount', 'unknown')}")
            print(f"  • Skillset Count: {stats.get('skillsetCount', 'unknown')}")
            
            # Check for vector-specific limits
            if 'vectorIndexSize' in stats:
                print(f"  • Vector Index Size: {stats.get('vectorIndexSize', 'unknown')} bytes")
            
            # Check limits
            limits = stats.get('limits', {})
            if limits:
                print(f"\n📏 Service Limits:")
                for key, value in limits.items():
                    print(f"  • {key}: {value}")
            
        else:
            print(f"❌ Failed to get service stats: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error checking service stats: {e}")
    
    # Get service info to check tier
    print(f"\n🏢 Checking Service Information:")
    service_name = config.search_service_name
    print(f"  • Service Name: {service_name}")
    print(f"  • Endpoint: {config.search_endpoint}")
    
    # Extract service info from endpoint if possible
    if "search.windows.net" in config.search_endpoint:
        print(f"  • Service Type: Azure AI Search")
        print(f"  • Region: {config.search_endpoint.split('//')[1].split('.')[0].replace(service_name, '').strip('-')}")

def check_index_without_vectors():
    """Test the index without vector components to see if basic search works."""
    
    headers = {
        "Content-Type": "application/json",
        "api-key": config.search_api_key
    }
    
    print(f"\n🔍 Testing Basic Search (Non-Vector) on idx-spofiles-integrated")
    print("=" * 60)
    
    search_url = f"{config.search_endpoint}/indexes/idx-spofiles-integrated/docs/search?api-version=2024-07-01"
    
    # Test basic text search without vectors
    search_payload = {
        "search": "iCore",
        "top": 3,
        "select": "id,title,content",
        "count": True,
        "searchMode": "any"
    }
    
    try:
        response = requests.post(search_url, headers=headers, json=search_payload)
        
        if response.status_code == 200:
            result = response.json()
            count = result.get('@odata.count', 0)
            print(f"✅ Basic search successful!")
            print(f"📊 Found {count} documents")
            
            if result.get('value'):
                for i, doc in enumerate(result['value'], 1):
                    print(f"  {i}. Title: {doc.get('title', 'No title')}")
                    print(f"     ID: {doc.get('id', 'No ID')[:20]}...")
                    content = doc.get('content', '')
                    if content:
                        print(f"     Content: {content[:80]}...")
                    print()
            else:
                print("⚠️  No results found")
        else:
            print(f"❌ Search failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def suggest_solutions():
    """Suggest solutions for vector quota issues."""
    
    print(f"\n💡 Solutions for Vector Index Quota = 0")
    print("=" * 60)
    
    print("🔧 Possible Solutions:")
    print()
    print("1️⃣ **Upgrade Service Tier**")
    print("   • Free tier: No vector support")
    print("   • Basic tier: Limited or no vector support") 
    print("   • Standard S1+: Full vector search support")
    print("   • Upgrade in Azure Portal > Search Service > Scale")
    print()
    
    print("2️⃣ **Create Index WITHOUT Vectors** (for immediate use)")
    print("   • Remove vector fields and vectorizers")
    print("   • Use only text-based search")
    print("   • Still works with Copilot Studio for basic text search")
    print()
    
    print("3️⃣ **Check Current Service Tier**")
    print("   • Go to Azure Portal")
    print("   • Find your search service")
    print("   • Check 'Pricing Tier' in Overview")
    print()
    
    print("4️⃣ **Alternative: Use Skillset-Based Approach**")
    print("   • Your previous idx-spofiles-v2 might work better")
    print("   • Uses skillsets instead of integrated vectorization")
    print("   • May work on lower tiers")

if __name__ == "__main__":
    check_search_service_limits()
    check_index_without_vectors()
    suggest_solutions()