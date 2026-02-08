import os
import aiohttp
import asyncio
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

async def test_nasa_api():
    """Test NASA API connection with different endpoints"""
    
    api_key = os.getenv("NASA_API_KEY", "DEMO_KEY")
    base_url = "https://api.nasa.gov/neo/rest/v1"
    
    print(f"🔑 Using API Key: {api_key[:8]}...")
    print(f"🌐 Base URL: {base_url}")
    print("-" * 50)
    
    test_endpoints = [
        {
            "name": "Today's Feed",
            "url": f"{base_url}/feed",
            "params": {
                "start_date": datetime.now().strftime("%Y-%m-%d"),
                "end_date": datetime.now().strftime("%Y-%m-%d"),
                "api_key": api_key
            }
        },
        {
            "name": "Asteroid Details (Apophis)",
            "url": f"{base_url}/neo/99942",
            "params": {"api_key": api_key}
        },
        {
            "name": "Browse All",
            "url": f"{base_url}/neo/browse",
            "params": {"api_key": api_key, "page": 0, "size": 1}
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        for test in test_endpoints:
            print(f"\n🔍 Testing: {test['name']}")
            print(f"   URL: {test['url']}")
            
            try:
                async with session.get(test['url'], params=test['params'], timeout=10) as response:
                    print(f"   Status: {response.status}")
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        if test['name'] == "Today's Feed":
                            count = data.get('element_count', 0)
                            print(f"   ✅ SUCCESS! Found {count} asteroids today")
                            if 'near_earth_objects' in data:
                                dates = list(data['near_earth_objects'].keys())
                                print(f"   📅 Dates with data: {dates}")
                                
                        elif test['name'] == "Asteroid Details (Apophis)":
                            name = data.get('name', 'Unknown')
                            print(f"   ✅ SUCCESS! Asteroid: {name}")
                            
                        elif test['name'] == "Browse All":
                            page_size = data.get('page', {}).get('size', 0)
                            print(f"   ✅ SUCCESS! Page size: {page_size}")
                            
                    elif response.status == 429:
                        print("   ❌ RATE LIMITED - Too many requests")
                        print("   💡 Try using your personal NASA API key")
                        print(f"   🔗 Get key at: https://api.nasa.gov/#signUp")
                        
                    elif response.status == 403:
                        print("   ❌ FORBIDDEN - Invalid API key")
                        
                    else:
                        text = await response.text()
                        print(f"   ❌ ERROR: {text[:100]}...")
                        
            except asyncio.TimeoutError:
                print("   ⏱️ TIMEOUT - NASA API is slow to respond")
            except Exception as e:
                print(f"   ❌ EXCEPTION: {str(e)}")
    
    print("\n" + "="*50)
    print("🎯 RECOMMENDATIONS:")
    print("1. Use your personal NASA API key for 1000 req/hour")
    print("2. Implement caching to reduce API calls")
    print("3. Use sample data as fallback (already implemented)")
    print("="*50)

if __name__ == "__main__":
    print("🚀 NASA API CONNECTION TEST")
    print("="*50)
    asyncio.run(test_nasa_api())
