import requests
import time

def test_endpoints():
    print("🚀 Testing Cosmic Watch Endpoints")
    print("=" * 50)
    
    endpoints = [
        ("Root", "/"),
        ("Health", "/health"),
        ("Dashboard", "/dashboard"),
        ("NASA Status", "/api/nasa/status"),
        ("NASA Real Data", "/api/nasa/real")
    ]
    
    base_url = "http://localhost:8000"
    
    for name, path in endpoints:
        url = base_url + path
        print(f"\n🔍 Testing {name}: {url}")
        
        try:
            start_time = time.time()
            response = requests.get(url, timeout=5)
            elapsed = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                print(f"   ✅ Status: {response.status_code} ({elapsed:.0f}ms)")
                if name == "NASA Real Data":
                    data = response.json()
                    print(f"   🪐 Asteroids: {data.get('total_asteroids', 0)}")
                    print(f"   📊 Source: {data.get('source', 'N/A')}")
            else:
                print(f"   ❌ Status: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print("   ❌ Connection failed - server may not be running")
            print("   💡 Run: python run.py")
            break
        except requests.exceptions.Timeout:
            print("   ⏱️ Timeout - server is slow")
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    print("\n" + "=" * 50)
    print("💡 If server is not running:")
    print("  1. Press CTRL+C in the terminal where server is running")
    print("  2. Run: python run.py")
    print("=" * 50)

if __name__ == "__main__":
    test_endpoints()
