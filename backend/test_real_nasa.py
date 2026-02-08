import os
import aiohttp
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import time
from dotenv import load_dotenv
import math

load_dotenv()

logger = logging.getLogger(__name__)

class WorkingNASAFetcher:
    """Working NASA API fetcher that uses real data"""
    
    def __init__(self):
        self.api_key = os.getenv("NASA_API_KEY", "DEMO_KEY")
        self.base_url = "https://api.nasa.gov/neo/rest/v1"
        self.session = None
        self.cache = {}
        self.cache_duration = 300  # 5 minutes
        
    async def init(self):
        """Initialize session"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=15)
            )
        logger.info("WorkingNASAFetcher initialized")
    
    async def close(self):
        """Close session"""
        if self.session:
            await self.session.close()
    
    async def fetch_real_data(self) -> Dict[str, Any]:
        """Fetch real NASA data"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Check cache first
            cache_key = f"nasa_real_{today}"
            if cache_key in self.cache:
                cached_time, data = self.cache[cache_key]
                if time.time() - cached_time < self.cache_duration:
                    logger.info("Using cached NASA data")
                    return data
            
            logger.info(f"Fetching real NASA data for {today}")
            
            url = f"{self.base_url}/feed"
            params = {
                "start_date": today,
                "end_date": today,
                "api_key": self.api_key
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    processed = await self._process_real_data(data, today)
                    
                    # Cache successful fetch
                    self.cache[cache_key] = (time.time(), processed)
                    logger.info(f"Successfully fetched {processed['element_count']} real asteroids")
                    
                    return processed
                else:
                    logger.warning(f"NASA API returned {response.status}")
                    return await self._get_enhanced_fallback(today)
                    
        except Exception as e:
            logger.error(f"Error fetching NASA data: {e}")
            return await self._get_enhanced_fallback(datetime.now().strftime("%Y-%m-%d"))
    
    async def _process_real_data(self, data: Dict[str, Any], date: str) -> Dict[str, Any]:
        """Process real NASA data with risk scoring"""
        processed_asteroids = []
        hazardous_count = 0
        total_count = data.get("element_count", 0)
        
        for date_str, asteroids in data.get("near_earth_objects", {}).items():
            for asteroid in asteroids:
                # Calculate risk score
                risk_score = self._calculate_risk_score(asteroid)
                threat_level = self._get_threat_level(risk_score)
                
                # Get close approach data
                miss_distance = 0
                velocity = 0
                if asteroid.get("close_approach_data"):
                    approach = asteroid["close_approach_data"][0]
                    miss_distance = float(approach.get("miss_distance", {}).get("kilometers", 0))
                    velocity = float(approach.get("relative_velocity", {}).get("kilometers_per_hour", 0))
                
                processed_asteroids.append({
                    "id": asteroid.get("id"),
                    "name": asteroid.get("name"),
                    "is_potentially_hazardous": asteroid.get("is_potentially_hazardous_asteroid", False),
                    "estimated_diameter_km": asteroid.get("estimated_diameter", {}).get("kilometers", {}).get("estimated_diameter_max", 0),
                    "miss_distance_km": miss_distance,
                    "relative_velocity_kph": velocity,
                    "risk_score": risk_score,
                    "threat_level": threat_level,
                    "absolute_magnitude": asteroid.get("absolute_magnitude_h"),
                    "orbiting_body": asteroid.get("close_approach_data", [{}])[0].get("orbiting_body", "Earth") if asteroid.get("close_approach_data") else "Earth",
                    "source": "nasa_real",
                    "is_sentry_object": asteroid.get("is_sentry_object", False)
                })
                
                if asteroid.get("is_potentially_hazardous_asteroid", False):
                    hazardous_count += 1
        
        return {
            "asteroids": processed_asteroids,
            "statistics": {
                "total_asteroids": total_count,
                "hazardous_count": hazardous_count,
                "hazardous_percentage": (hazardous_count / total_count * 100) if total_count > 0 else 0,
                "average_risk": sum(a["risk_score"] for a in processed_asteroids) / len(processed_asteroids) if processed_asteroids else 0
            },
            "date": date,
            "element_count": total_count,
            "source": "nasa_api_real",
            "is_real_data": True,
            "timestamp": datetime.now().isoformat(),
            "message": "✅ Real NASA data"
        }
    
    def _calculate_risk_score(self, asteroid: Dict[str, Any]) -> float:
        """Calculate risk score based on real asteroid data"""
        score = 0
        
        # 1. Hazardous status
        if asteroid.get("is_potentially_hazardous_asteroid", False):
            score += 40
        
        # 2. Diameter (larger = more dangerous)
        try:
            diameter = asteroid["estimated_diameter"]["kilometers"]["estimated_diameter_max"]
            if diameter > 0:
                # Logarithmic scale
                diameter_score = min(30, 15 * math.log10(diameter * 1000))
                score += diameter_score
        except:
            pass
        
        # 3. Miss distance (closer = more dangerous)
        try:
            if asteroid.get("close_approach_data"):
                approach = asteroid["close_approach_data"][0]
                miss_km = float(approach["miss_distance"]["kilometers"])
                miss_ld = miss_km / 384400  # Lunar distances
                
                if miss_ld <= 0.1:
                    score += 25
                elif miss_ld <= 0.5:
                    score += 15
                elif miss_ld <= 1:
                    score += 10
                elif miss_ld <= 5:
                    score += 5
        except:
            pass
        
        # 4. Velocity (faster = more dangerous)
        try:
            if asteroid.get("close_approach_data"):
                velocity = float(asteroid["close_approach_data"][0]["relative_velocity"]["kilometers_per_hour"])
                if velocity > 80000:
                    score += 10
                elif velocity > 60000:
                    score += 7
                elif velocity > 40000:
                    score += 4
        except:
            pass
        
        return min(100, round(score, 1))
    
    def _get_threat_level(self, score: float) -> str:
        """Convert score to threat level"""
        if score >= 70:
            return "🚨 CRITICAL"
        elif score >= 50:
            return "⚠️ HIGH"
        elif score >= 30:
            return "🔶 MODERATE"
        elif score >= 10:
            return "📉 LOW"
        else:
            return "✅ MINIMAL"
    
    async def _get_enhanced_fallback(self, date: str) -> Dict[str, Any]:
        """Get enhanced fallback data based on real asteroid names"""
        logger.info("Using enhanced fallback data")
        
        # Use real asteroid names from your successful test
        fallback_asteroids = [
            {
                "id": "3137864",
                "name": "(2002 TS69)",
                "is_potentially_hazardous": False,
                "estimated_diameter_km": 0.078,
                "miss_distance_km": 38344523,
                "relative_velocity_kph": 15302,
                "risk_score": 12.5,
                "threat_level": "📉 LOW",
                "absolute_magnitude": 24.4,
                "orbiting_body": "Earth",
                "source": "fallback_real_data",
                "note": "Based on real NASA asteroid data"
            },
            {
                "id": "3467218",
                "name": "(2009 SY)",
                "is_potentially_hazardous": False,
                "estimated_diameter_km": 0.150,
                "miss_distance_km": 41890194,
                "relative_velocity_kph": 80338,
                "risk_score": 28.3,
                "threat_level": "🔶 MODERATE",
                "absolute_magnitude": 22.99,
                "orbiting_body": "Earth",
                "source": "fallback_real_data",
                "note": "Based on real NASA asteroid data"
            },
            {
                "id": "3799250",
                "name": "(2018 CE1)",
                "is_potentially_hazardous": False,
                "estimated_diameter_km": 0.365,
                "miss_distance_km": 55910608,
                "relative_velocity_kph": 65710,
                "risk_score": 35.7,
                "threat_level": "🔶 MODERATE",
                "absolute_magnitude": 21.06,
                "orbiting_body": "Earth",
                "source": "fallback_real_data",
                "note": "Based on real NASA asteroid data"
            }
        ]
        
        return {
            "asteroids": fallback_asteroids,
            "statistics": {
                "total_asteroids": len(fallback_asteroids),
                "hazardous_count": 0,
                "hazardous_percentage": 0,
                "average_risk": sum(a["risk_score"] for a in fallback_asteroids) / len(fallback_asteroids)
            },
            "date": date,
            "element_count": len(fallback_asteroids),
            "source": "enhanced_fallback",
            "is_real_data": False,
            "timestamp": datetime.now().isoformat(),
            "message": "Using enhanced fallback data based on real asteroid names"
        }

# Global instance
nasa_fetcher = WorkingNASAFetcher()

async def test_real_integration():
    """Test the real NASA integration"""
    print("🚀 TESTING REAL NASA INTEGRATION")
    print("=" * 60)
    
    await nasa_fetcher.init()
    
    print(f"🔑 API Key: {nasa_fetcher.api_key[:8]}...")
    print(f"🌐 Base URL: {nasa_fetcher.base_url}")
    print("-" * 60)
    
    data = await nasa_fetcher.fetch_real_data()
    
    print(f"📅 Date: {data['date']}")
    print(f"📊 Source: {data['source']}")
    print(f"✅ Real NASA Data: {data.get('is_real_data', False)}")
    print(f"📈 Message: {data.get('message', 'N/A')}")
    print(f"🪐 Total Asteroids: {data['statistics']['total_asteroids']}")
    print(f"⚠️ Hazardous: {data['statistics']['hazardous_count']}")
    print(f"📊 Hazardous %: {data['statistics']['hazardous_percentage']:.1f}%")
    print(f"🎯 Average Risk: {data['statistics']['average_risk']:.1f}")
    
    print("\n🪐 Sample Asteroids:")
    for i, asteroid in enumerate(data['asteroids'][:3], 1):
        print(f"  {i}. {asteroid['name']}")
        print(f"     Risk: {asteroid['risk_score']} | Threat: {asteroid['threat_level']}")
        print(f"     Diameter: {asteroid['estimated_diameter_km']:.3f} km")
        print(f"     Distance: {asteroid['miss_distance_km']/1000000:.1f}M km")
        print(f"     Source: {asteroid['source']}")
        print()
    
    print("=" * 60)
    
    if data.get('is_real_data'):
        print("🎉 SUCCESS: Real NASA data is being used!")
        print("✅ Your API key is working perfectly")
    else:
        print("⚠️ Using enhanced fallback data")
        print("💡 Real data was unavailable (rate limit or network issue)")
    
    await nasa_fetcher.close()

if __name__ == "__main__":
    asyncio.run(test_real_integration())
