import os
import aiohttp
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import math

logger = logging.getLogger(__name__)

# NASA API configuration
NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")
BASE_URL = "https://api.nasa.gov/neo/rest/v1"

async def fetch_nasa_data(endpoint: str, params: dict) -> Dict[str, Any]:
    """Fetch data from NASA API"""
    url = f"{BASE_URL}/{endpoint}"
    params["api_key"] = NASA_API_KEY
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"NASA API error: {response.status}")
                    return {}
    except Exception as e:
        logger.error(f"Error fetching NASA data: {e}")
        return {}

async def fetch_todays_asteroids() -> List[Dict[str, Any]]:
    """Fetch today's asteroids"""
    today = datetime.now().strftime("%Y-%m-%d")
    params = {
        "start_date": today,
        "end_date": today
    }
    
    data = await fetch_nasa_data("feed", params)
    
    if not data:
        # Return sample data if NASA API fails
        return get_sample_asteroids()
    
    asteroids = []
    for date_str, neo_list in data.get("near_earth_objects", {}).items():
        for asteroid in neo_list:
            risk_score = calculate_risk_score(
                diameter=asteroid.get("estimated_diameter", {}).get("kilometers", {}).get("estimated_diameter_max", 0),
                velocity=float(asteroid.get("close_approach_data", [{}])[0].get("relative_velocity", {}).get("kilometers_per_hour", 0)) if asteroid.get("close_approach_data") else 0,
                distance=float(asteroid.get("close_approach_data", [{}])[0].get("miss_distance", {}).get("kilometers", 0)) if asteroid.get("close_approach_data") else 0,
                is_hazardous=asteroid.get("is_potentially_hazardous_asteroid", False)
            )
            
            asteroids.append({
                "id": asteroid.get("id"),
                "name": asteroid.get("name"),
                "is_potentially_hazardous": asteroid.get("is_potentially_hazardous_asteroid", False),
                "estimated_diameter_km": asteroid.get("estimated_diameter", {}).get("kilometers", {}).get("estimated_diameter_max", 0),
                "miss_distance_km": float(asteroid.get("close_approach_data", [{}])[0].get("miss_distance", {}).get("kilometers", 0)) if asteroid.get("close_approach_data") else 0,
                "relative_velocity_kph": float(asteroid.get("close_approach_data", [{}])[0].get("relative_velocity", {}).get("kilometers_per_hour", 0)) if asteroid.get("close_approach_data") else 0,
                "risk_score": risk_score,
                "threat_level": get_threat_level(risk_score)
            })
    
    return asteroids

async def fetch_hazardous_asteroids() -> List[Dict[str, Any]]:
    """Fetch only hazardous asteroids"""
    all_asteroids = await fetch_todays_asteroids()
    return [a for a in all_asteroids if a["is_potentially_hazardous"]]

def calculate_risk_score(diameter: float, velocity: float, distance: float, is_hazardous: bool) -> float:
    """Calculate risk score for an asteroid"""
    score = 0
    
    # Diameter contribution (max 30)
    if diameter > 0:
        score += min(30, diameter * 20)
    
    # Velocity contribution (max 25)
    if velocity > 0:
        score += min(25, velocity / 3000)
    
    # Distance contribution (closer = higher score, max 40)
    if distance > 0:
        distance_ld = distance / 384400  # Convert to lunar distances
        if distance_ld <= 0.1:
            score += 40
        elif distance_ld <= 0.5:
            score += 30
        elif distance_ld <= 1:
            score += 20
        elif distance_ld <= 5:
            score += 10
    
    # Hazardous bonus
    if is_hazardous:
        score += 15
    
    return min(100, round(score, 1))

def get_threat_level(score: float) -> str:
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

def get_sample_asteroids() -> List[Dict[str, Any]]:
    """Get sample asteroid data for fallback"""
    return [
        {
            "id": "3542519",
            "name": "(2010 PK9)",
            "is_potentially_hazardous": True,
            "estimated_diameter_km": 0.284,
            "miss_distance_km": 7230000,
            "relative_velocity_kph": 67600,
            "risk_score": 65,
            "threat_level": "⚠️ HIGH"
        },
        {
            "id": "3726710",
            "name": "(2015 RC)",
            "is_potentially_hazardous": False,
            "estimated_diameter_km": 0.041,
            "miss_distance_km": 15400000,
            "relative_velocity_kph": 54200,
            "risk_score": 15,
            "threat_level": "📉 LOW"
        },
        {
            "id": "2465633",
            "name": "465633 (2009 JR5)",
            "is_potentially_hazardous": True,
            "estimated_diameter_km": 1.2,
            "miss_distance_km": 12500000,
            "relative_velocity_kph": 58900,
            "risk_score": 75,
            "threat_level": "🚨 CRITICAL"
        },
        {
            "id": "3550117",
            "name": "(2010 VB)",
            "is_potentially_hazardous": False,
            "estimated_diameter_km": 0.045,
            "miss_distance_km": 53200000,
            "relative_velocity_kph": 43849,
            "risk_score": 8,
            "threat_level": "✅ MINIMAL"
        }
    ]