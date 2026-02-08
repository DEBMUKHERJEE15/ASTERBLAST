import os
from fastapi import FastAPI, HTTPException
from datetime import datetime
import aiohttp
import asyncio

app = FastAPI()

@app.get("/api/nasa/real")
async def get_real_nasa_data():
    """Get real NASA asteroid data"""
    api_key = os.getenv("NASA_API_KEY", "DEMO_KEY")
    today = datetime.now().strftime("%Y-%m-%d")
    
    url = "https://api.nasa.gov/neo/rest/v1/feed"
    params = {
        "start_date": today,
        "end_date": today,
        "api_key": api_key
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Simple processing
                    asteroids = []
                    for date_str, neo_list in data.get("near_earth_objects", {}).items():
                        for asteroid in neo_list:
                            asteroids.append({
                                "id": asteroid.get("id"),
                                "name": asteroid.get("name"),
                                "is_hazardous": asteroid.get("is_potentially_hazardous_asteroid", False),
                                "diameter_km": asteroid.get("estimated_diameter", {}).get("kilometers", {}).get("estimated_diameter_max", 0),
                                "distance_km": float(asteroid.get("close_approach_data", [{}])[0].get("miss_distance", {}).get("kilometers", 0)) if asteroid.get("close_approach_data") else 0,
                                "velocity_kph": float(asteroid.get("close_approach_data", [{}])[0].get("relative_velocity", {}).get("kilometers_per_hour", 0)) if asteroid.get("close_approach_data") else 0
                            })
                    
                    return {
                        "success": True,
                        "date": today,
                        "total_asteroids": data.get("element_count", 0),
                        "asteroids": asteroids[:10],  # First 10
                        "source": "NASA API - Real Data",
                        "is_real_data": True,
                        "api_key": api_key[:8] + "...",
                        "timestamp": datetime.now().isoformat(),
                        "message": "✅ Real NASA data fetched successfully"
                    }
                else:
                    return {
                        "success": False,
                        "date": today,
                        "message": f"NASA API returned status {response.status}",
                        "source": "NASA API",
                        "is_real_data": False,
                        "timestamp": datetime.now().isoformat()
                    }
                    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
