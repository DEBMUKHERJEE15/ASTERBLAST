#!/usr/bin/env python3
"""
Test script for Cosmic Watch Backend
"""
import asyncio
import aiohttp
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:8000/api"

async def test_health():
    """Test health endpoint"""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/health") as response:
            data = await response.json()
            print("✅ Health Check:", json.dumps(data, indent=2))
            return response.status == 200

async def test_register(session):
    """Test user registration"""
    user_data = {
        "email": f"test_{datetime.now().timestamp()}@example.com",
        "username": f"testuser_{datetime.now().timestamp()}",
        "password": "TestPass123!",
        "is_researcher": False
    }
    
    async with session.post(f"{BASE_URL}/auth/register", json=user_data) as response:
        data = await response.json()
        if response.status == 200:
            print("✅ Registration successful")
            return data["tokens"]["access_token"]
        else:
            print("❌ Registration failed:", data)
            return None

async def test_login(session, email, password):
    """Test user login"""
    form_data = {
        "username": email,
        "password": password
    }
    
    async with session.post(f"{BASE_URL}/auth/login", data=form_data) as response:
        data = await response.json()
        if response.status == 200:
            print("✅ Login successful")
            return data["tokens"]["access_token"]
        else:
            print("❌ Login failed:", data)
            return None

async def test_asteroid_feed(session, token):
    """Test asteroid feed endpoint"""
    headers = {"Authorization": f"Bearer {token}"}
    async with session.get(f"{BASE_URL}/asteroids/feed?days=1", headers=headers) as response:
        data = await response.json()
        if response.status == 200:
            print(f"✅ Asteroid feed: {len(data.get('data', []))} asteroids")
            return True
        else:
            print("❌ Asteroid feed failed:", data)
            return False

async def test_asteroid_details(session, token):
    """Test asteroid details endpoint"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get a sample asteroid ID from feed
    async with session.get(f"{BASE_URL}/asteroids/feed?days=1&size=1", headers=headers) as response:
        feed_data = await response.json()
        if feed_data.get("data"):
            asteroid_id = feed_data["data"][0]["id"]
            
            # Get details
            async with session.get(f"{BASE_URL}/asteroids/{asteroid_id}", headers=headers) as detail_response:
                detail_data = await detail_response.json()
                if detail_response.status == 200:
                    print(f"✅ Asteroid details: {detail_data.get('name', 'Unknown')}")
                    return True
                else:
                    print("❌ Asteroid details failed:", detail_data)
                    return False
        return False

async def test_statistics(session, token):
    """Test statistics endpoint"""
    headers = {"Authorization": f"Bearer {token}"}
    async with session.get(f"{BASE_URL}/asteroids/statistics/summary?period_days=7", headers=headers) as response:
        data = await response.json()
        if response.status == 200:
            print(f"✅ Statistics: {data.get('total_asteroids', 0)} asteroids")
            return True
        else:
            print("❌ Statistics failed:", data)
            return False

async def test_monitoring(session, token):
    """Test monitoring endpoints"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test cache stats
    async with session.get(f"{BASE_URL}/monitoring/cache/stats", headers=headers) as response:
        data = await response.json()
        if response.status == 200:
            print("✅ Monitoring cache stats")
            return True
        else:
            print("❌ Monitoring failed:", data)
            return False

async def run_all_tests():
    """Run all tests"""
    print("🧪 Running Cosmic Watch Backend Tests")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # Test health endpoint
        if not await test_health():
            print("❌ Health check failed, exiting...")
            return False
        
        # Test registration and login
        token = await test_register(session)
        if not token:
            print("❌ Registration failed, exiting...")
            return False
        
        # Test authenticated endpoints
        tests = [
            ("Asteroid Feed", test_asteroid_feed(session, token)),
            ("Asteroid Details", test_asteroid_details(session, token)),
            ("Statistics", test_statistics(session, token)),
            ("Monitoring", test_monitoring(session, token))
        ]
        
        results = await asyncio.gather(*[test for _, test in tests])
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 Test Summary:")
        for (name, _), result in zip(tests, results):
            print(f"  {'✅' if result else '❌'} {name}")
        
        success_count = sum(results)
        total_tests = len(tests)
        
        print(f"\n🎯 {success_count}/{total_tests} tests passed")
        
        return success_count == total_tests

if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test runner error: {e}")
        sys.exit(1)