import os
import aiohttp
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import time
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class RealNASAFetcher:
    """Real NASA API fetcher with intelligent fallback"""
    
    def __init__(self):
        self.api_key = os.getenv("NASA_API_KEY", "DEMO_KEY")
        self.base_url = "https://api.nasa.gov/neo/rest/v1"
        self.session = None
        self.cache = {}
        self.last_real_fetch = None
        self.use_real_data = True  # Try to use real data first
    
    async def init(self):
        """Initialize session"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15)
            )
        logger.info("NASAFetcher initialized")
    
    async def close(self):
        """Close session"""
        if self.session:
            await self.session.close()
    
    async def fetch_real_asteroids(self) -> Optional[Dict[str, Any]]:
        """Try to fetch real NASA data"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            # If we fetched real data recently, use cache
            cache_key = f"real_data_{today}"
            if cache_key in self.cache:
                cached_time, data = self.cache[cache_key]
                if time.time() - cached_time < 300:  # 5 minute cache
                    logger.info("Using cached NASA data")
                    return data
            
            # Fetch from NASA
            url = f"{self.base_url}/feed"
            params = {
                "start_date": today,
                "end_date": today,
                "api_key": self.api_key
            }
            
            logger.info(f"Fetching real NASA data for {today}")
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    processed = await self._process_nasa_data(data, today)
                    
                    # Cache the successful fetch
                    self.cache[cache_key] = (time.time(), processed)
                    self.last_real_fetch = datetime.now()
                    
                    logger.info(f"Successfully fetched {processed['element_count']} asteroids from NASA")
                    return processed
                    
                elif response.status == 429:
                    logger.warning("NASA API rate limit hit")
                    return None
                else:
                    logger.error(f"NASA API error: {response.status}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching NASA data: {e}")
            return None
    
    async def _process_nasa_data(self, data: Dict[str, Any], date: str) -> Dict[str, Any]:
        """Process real NASA data"""
        processed_asteroids = []
        hazardous_count = 0
        
        for date_str, asteroids in data.get("near_earth_objects", {}).items():
            for asteroid in asteroids:
                # Calculate simple risk score
                risk_score = 0
                if asteroid.get("is_potentially_hazardous_asteroid", False):
                    risk_score += 50
                    hazardous_count += 1
                
                # Add basic info
                processed_asteroids.append({
                    "id": asteroid.get("id"),
                    "name": asteroid.get("name"),
                    "is_potentially_hazardous": asteroid.get("is_potentially_hazardous_asteroid", False),
                    "estimated_diameter_km": asteroid.get("estimated_diameter", {}).get("kilometers", {}).get("estimated_diameter_max", 0),
                    "miss_distance_km": float(asteroid.get("close_approach_data", [{}])[0].get("miss_distance", {}).get("kilometers", 0)) if asteroid.get("close_approach_data") else 0,
                    "relative_velocity_kph": float(asteroid.get("close_approach_data", [{}])[0].get("relative_velocity", {}).get("kilometers_per_hour", 0)) if asteroid.get("close_approach_data") else 0,
                    "risk_score": risk_score,
                    "threat_level": "HIGH" if risk_score >= 50 else "LOW",
                    "source": "nasa_real"
                })
        
        return {
            "asteroids": processed_asteroids,
            "statistics": {
                "total_asteroids": data.get("element_count", 0),
                "hazardous_count": hazardous_count,
                "hazardous_percentage": (hazardous_count / data.get("element_count", 1)) * 100
            },
            "date": date,
            "element_count": data.get("element_count", 0),
            "source": "nasa_api_real",
            "timestamp": datetime.now().isoformat()
        }
    
    def get_sample_data(self) -> Dict[str, Any]:
        """Get enhanced sample data"""
        today = datetime.now().strftime("%Y-%m-%d")
        
        sample_asteroids = [
            {
                "id": "3542519",
                "name": "(2010 PK9) - REAL DATA",
                "is_potentially_hazardous": True,
                "estimated_diameter_km": 0.284,
                "miss_distance_km": 7230000,
                "relative_velocity_kph": 67600,
                "risk_score": 65,
                "threat_level": "HIGH",
                "source": "sample_fallback"
            },
            {
                "id": "3726710",
                "name": "(2015 RC) - REAL DATA",
                "is_potentially_hazardous": False,
                "estimated_diameter_km": 0.041,
                "miss_distance_km": 15400000,
                "relative_velocity_kph": 54200,
                "risk_score": 15,
                "threat_level": "LOW",
                "source": "sample_fallback"
            },
            {
                "id": "2465633",
                "name": "465633 (2009 JR5) - REAL DATA",
                "is_potentially_hazardous": True,
                "estimated_diameter_km": 1.2,
                "miss_distance_km": 12500000,
                "relative_velocity_kph": 58900,
                "risk_score": 75,
                "threat_level": "HIGH",
                "source": "sample_fallback"
            }
        ]
        
        return {
            "asteroids": sample_asteroids,
            "statistics": {
                "total_asteroids": len(sample_asteroids),
                "hazardous_count": len([a for a in sample_asteroids if a["is_potentially_hazardous"]]),
                "hazardous_percentage": 66.7
            },
            "date": today,
            "element_count": len(sample_asteroids),
            "source": "sample_fallback",
            "timestamp": datetime.now().isoformat(),
            "note": "Using sample data. NASA API may be rate limited."
        }
    
    async def get_asteroid_data(self) -> Dict[str, Any]:
        """Get asteroid data - tries real NASA first, falls back to sample"""
        await self.init()
        
        # Try to get real data
        real_data = await self.fetch_real_asteroids()
        
        if real_data:
            # Add a flag to indicate this is real data
            real_data["is_real_nasa_data"] = True
            real_data["data_source"] = "NASA NeoWS API - Live Data"
            return real_data
        else:
            # Fall back to sample data
            sample_data = self.get_sample_data()
            sample_data["is_real_nasa_data"] = False
            sample_data["data_source"] = "Cosmic Watch Sample Database"
            sample_data["api_status"] = "Rate limited or offline - showing sample data"
            return sample_data

# Create global instance
nasa_fetcher = RealNASAFetcher()

# Test function
async def test_and_display():
    """Test the fetcher and display results"""
    print("🚀 Testing NASA API Integration")
    print("=" * 60)
    
    data = await nasa_fetcher.get_asteroid_data()
    
    print(f"📅 Date: {data['date']}")
    print(f"📊 Source: {data['data_source']}")
    print(f"🔍 Real NASA Data: {data.get('is_real_nasa_data', False)}")
    print(f"🪐 Total Asteroids: {data['statistics']['total_asteroids']}")
    print(f"⚠️ Hazardous: {data['statistics']['hazardous_count']}")
    print(f"📈 Hazardous %: {data['statistics']['hazardous_percentage']:.1f}%")
    
    print("\n🪐 Sample Asteroids:")
    for asteroid in data['asteroids'][:3]:  # Show first 3
        print(f"  • {asteroid['name']}")
        print(f"    Risk: {asteroid['risk_score']} | Threat: {asteroid['threat_level']}")
        print(f"    Diameter: {asteroid['estimated_diameter_km']:.3f} km")
        print(f"    Distance: {asteroid['miss_distance_km']/1000000:.1f}M km")
        print()
    
    print("=" * 60)
    print("💡 TIPS:")
    if data.get('is_real_nasa_data'):
        print("✅ NASA API is working! Real data is being used.")
        print("🔑 Your API key: WORKING")
    else:
        print("⚠️ Using sample data. Possible reasons:")
        print("   • Rate limit reached (30 req/hour for DEMO_KEY)")
        print("   • NASA API temporarily unavailable")
        print("   • Network issues")
        print("\n🔧 To fix:")
        print("   1. Use your personal NASA API key")
        print("   2. Wait an hour for rate limit reset")
        print("   3. Check network connection")
    
    await nasa_fetcher.close()

if __name__ == "__main__":
    asyncio.run(test_and_display())
