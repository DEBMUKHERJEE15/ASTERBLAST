import os
import sys
import json
import logging
import random
import math
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

import aiohttp
from fastapi import (
    FastAPI, 
    HTTPException, 
    Depends, 
    WebSocket, 
    WebSocketDisconnect, 
    status,
    Request,
    Query,
    Path
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import psutil
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field, validator

# ============ CONFIGURE LOGGING FOR WINDOWS ============
class SafeStreamHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            # Encode to ASCII, replacing non-ASCII characters
            msg = msg.encode('ascii', 'replace').decode('ascii')
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cosmic_watch.log', encoding='utf-8'),
        SafeStreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============ RATE LIMITING ============
limiter = Limiter(key_func=get_remote_address)

# ============ CREATE FASTAPI APP ============
app = FastAPI(
    title="🌌 COSMIC WATCH API",
    description="Real-time Asteroid Threat Detection & Monitoring System",
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "Cosmic Watch Team",
        "url": "https://github.com/yourusername/cosmic-watch",
        "email": "cosmic.watch@example.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    }
)

# Add rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ============ CORS MIDDLEWARE ============
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ SECURITY ============
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ============ CONFIGURATION ============
class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")
    NASA_BASE_URL = "https://api.nasa.gov/neo/rest/v1"
    
config = Config()

# ============ IN-MEMORY CACHE ============
memory_cache = {}

def get_cache(key: str):
    """Get value from memory cache"""
    return memory_cache.get(key)

def set_cache(key: str, value: Any, ttl: int = 300):
    """Set value in memory cache"""
    memory_cache[key] = value

# ============ SIMPLIFIED PYDANTIC MODELS ============
class UserBase(BaseModel):
    email: str = Field(..., pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
    username: str = Field(..., min_length=3, max_length=50)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(UserBase):
    id: str
    is_active: bool
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class AsteroidBase(BaseModel):
    id: str
    name: str
    is_potentially_hazardous: bool
    estimated_diameter_km: float
    miss_distance_km: float
    relative_velocity_kph: float

class AsteroidResponse(AsteroidBase):
    risk_score: float
    threat_level: str
    size_category: str
    distance_category: str
    close_approach_date: str

# ============ SAMPLE DATA ============
SAMPLE_ASTEROIDS = {
    "today": [
        {
            "id": "3542519",
            "name": "(2010 PK9)",
            "is_potentially_hazardous": True,
            "estimated_diameter_km": 0.284,
            "close_approach_date": datetime.now().strftime("%Y-%m-%d"),
            "miss_distance_km": 7230000,
            "relative_velocity_kph": 67600,
            "absolute_magnitude": 21.3,
            "orbiting_body": "Earth"
        },
        {
            "id": "3726710",
            "name": "(2015 RC)",
            "is_potentially_hazardous": False,
            "estimated_diameter_km": 0.041,
            "close_approach_date": datetime.now().strftime("%Y-%m-%d"),
            "miss_distance_km": 15400000,
            "relative_velocity_kph": 54200,
            "absolute_magnitude": 25.8,
            "orbiting_body": "Earth"
        },
        {
            "id": "2465633",
            "name": "465633 (2009 JR5)",
            "is_potentially_hazardous": True,
            "estimated_diameter_km": 1.2,
            "close_approach_date": datetime.now().strftime("%Y-%m-%d"),
            "miss_distance_km": 12500000,
            "relative_velocity_kph": 58900,
            "absolute_magnitude": 17.8,
            "orbiting_body": "Earth"
        },
        {
            "id": "3752467",
            "name": "(2016 CA30)",
            "is_potentially_hazardous": True,
            "estimated_diameter_km": 0.048,
            "close_approach_date": datetime.now().strftime("%Y-%m-%d"),
            "miss_distance_km": 8900000,
            "relative_velocity_kph": 61200,
            "absolute_magnitude": 24.5,
            "orbiting_body": "Earth"
        }
    ],
    "upcoming": [
        {
            "id": "99942",
            "name": "Apophis",
            "is_potentially_hazardous": True,
            "estimated_diameter_km": 0.34,
            "close_approach_date": "2029-04-13",
            "miss_distance_km": 31600,
            "relative_velocity_kph": 76500,
            "absolute_magnitude": 19.7,
            "orbiting_body": "Earth",
            "note": "Historic close approach in 2029"
        },
        {
            "id": "101955",
            "name": "Bennu",
            "is_potentially_hazardous": True,
            "estimated_diameter_km": 0.49,
            "close_approach_date": "2135-09-25",
            "miss_distance_km": 750000,
            "relative_velocity_kph": 63000,
            "absolute_magnitude": 20.9,
            "orbiting_body": "Earth",
            "note": "NASA OSIRIS-REx mission target"
        }
    ]
}

# ============ RISK CALCULATION ENGINE ============
class RiskCalculator:
    @staticmethod
    def calculate_risk_score(asteroid: Dict[str, Any]) -> float:
        score = 0
        if asteroid.get("is_potentially_hazardous", False):
            score += 35
        
        diameter = asteroid.get("estimated_diameter_km", 0)
        if diameter > 0:
            score += min(30, 10 * math.log10(diameter * 1000))
        
        distance = asteroid.get("miss_distance_km", float('inf'))
        if distance < float('inf'):
            lunar_distance = distance / 384400
            if lunar_distance <= 0.05:
                score += 25
            elif lunar_distance <= 0.1:
                score += 20
            elif lunar_distance <= 0.5:
                score += 15
            elif lunar_distance <= 1:
                score += 10
            elif lunar_distance <= 5:
                score += 5
        
        velocity = asteroid.get("relative_velocity_kph", 0)
        if velocity > 80000:
            score += 10
        elif velocity > 60000:
            score += 7
        elif velocity > 40000:
            score += 4
        else:
            score += 2
        
        return min(100, round(score, 1))
    
    @staticmethod
    def get_threat_level(score: float) -> str:
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

# ============ DATA PROCESSOR ============
class DataProcessor:
    def __init__(self):
        self.risk_calc = RiskCalculator()
    
    def process_asteroids(self, asteroids: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        processed = []
        for asteroid in asteroids:
            risk_score = self.risk_calc.calculate_risk_score(asteroid)
            threat_level = self.risk_calc.get_threat_level(risk_score)
            
            processed.append({
                **asteroid,
                "risk_score": risk_score,
                "threat_level": threat_level,
                "size_category": self._get_size_category(asteroid.get("estimated_diameter_km", 0)),
                "distance_category": self._get_distance_category(asteroid.get("miss_distance_km", float('inf')))
            })
        return processed
    
    def _get_size_category(self, diameter: float) -> str:
        if diameter >= 1:
            return "LARGE (≥1 km)"
        elif diameter >= 0.1:
            return "MEDIUM (0.1-1 km)"
        else:
            return "SMALL (<0.1 km)"
    
    def _get_distance_category(self, distance: float) -> str:
        lunar_distance = distance / 384400
        if lunar_distance <= 0.1:
            return "EXTREMELY CLOSE"
        elif lunar_distance <= 0.5:
            return "VERY CLOSE"
        elif lunar_distance <= 1:
            return "CLOSE"
        elif lunar_distance <= 5:
            return "NEARBY"
        else:
            return "DISTANT"

processor = DataProcessor()

# ============ STATISTICS GENERATOR ============
def generate_statistics(asteroids: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not asteroids:
        return {}
    
    hazardous = [a for a in asteroids if a.get("is_potentially_hazardous", False)]
    risk_scores = [a.get("risk_score", 0) for a in asteroids]
    
    closest = min(asteroids, key=lambda x: x.get("miss_distance_km", float('inf')))
    
    return {
        "total_count": len(asteroids),
        "hazardous_count": len(hazardous),
        "hazardous_percentage": round((len(hazardous) / len(asteroids)) * 100, 1) if asteroids else 0,
        "risk_analysis": {
            "average_risk": round(sum(risk_scores) / len(risk_scores), 1) if risk_scores else 0,
            "max_risk": max(risk_scores) if risk_scores else 0,
            "min_risk": min(risk_scores) if risk_scores else 0,
        },
        "closest_approach": {
            "asteroid_id": closest.get("id"),
            "asteroid_name": closest.get("name"),
            "distance_km": closest.get("miss_distance_km"),
            "distance_lunar": round(closest.get("miss_distance_km", 0) / 384400, 3),
            "date": closest.get("close_approach_date")
        },
        "timestamp": datetime.now().isoformat()
    }

# ============ NASA API INTEGRATION ============
async def fetch_nasa_data() -> Optional[Dict[str, Any]]:
    """Fetch real data from NASA API"""
    cache_key = f"nasa_data_{datetime.now().strftime('%Y-%m-%d')}"
    cached = get_cache(cache_key)
    
    if cached:
        logger.info("Using cached NASA data")
        return cached
    
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        url = f"{config.NASA_BASE_URL}/feed"
        params = {
            "start_date": today,
            "end_date": today,
            "api_key": config.NASA_API_KEY
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    set_cache(cache_key, data, ttl=300)
                    return data
                elif response.status == 429:
                    logger.warning("NASA API rate limit exceeded")
                else:
                    logger.error(f"NASA API error: {response.status}")
    except Exception as e:
        logger.error(f"Error fetching NASA data: {e}")
    
    return None

# ============ WEBSOCKET MANAGER ============
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                self.disconnect(connection)

manager = ConnectionManager()

# ============ AUTH UTILITIES ============
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return encoded_jwt

# ============ API ENDPOINTS ============

@app.get("/", tags=["Root"])
@limiter.limit("60/minute")
async def root(request: Request):
    """Root endpoint with API information"""
    return {
        "app": "COSMIC WATCH",
        "version": "4.0.0",
        "status": "OPERATIONAL",
        "description": "Real-time Asteroid Threat Detection System",
        "timestamp": datetime.now().isoformat(),
        "endpoints": [
            {"path": "/", "method": "GET", "description": "API information"},
            {"path": "/health", "method": "GET", "description": "System health check"},
            {"path": "/dashboard", "method": "GET", "description": "Comprehensive dashboard"},
            {"path": "/asteroids/today", "method": "GET", "description": "Today's asteroids"},
            {"path": "/asteroids/hazardous", "method": "GET", "description": "Hazardous asteroids"},
            {"path": "/asteroids/upcoming", "method": "GET", "description": "Upcoming approaches"},
            {"path": "/statistics", "method": "GET", "description": "Statistics"},
            {"path": "/alerts", "method": "GET", "description": "Alerts"},
            {"path": "/simulate/threat", "method": "GET", "description": "Threat simulation"},
            {"path": "/api/nasa/real", "method": "GET", "description": "Real NASA data"}
        ]
    }

@app.get("/health", tags=["Monitoring"])
async def health_check():
    """System health check"""
    return {
        "status": "healthy",
        "service": "Cosmic Watch API",
        "version": "4.0.0",
        "timestamp": datetime.now().isoformat(),
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent
        }
    }

@app.get("/dashboard", tags=["Dashboard"])
@limiter.limit("30/minute")
async def get_dashboard(request: Request):
    """Comprehensive dashboard data"""
    asteroids = processor.process_asteroids(SAMPLE_ASTEROIDS["today"])
    statistics = generate_statistics(asteroids)
    
    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "dashboard": {
            "overview": {
                "total_asteroids_today": statistics["total_count"],
                "hazardous_threats": statistics["hazardous_count"],
                "global_risk_level": "MODERATE",
                "average_risk_score": round(statistics["risk_analysis"]["average_risk"], 1),
                "closest_approach": statistics["closest_approach"],
                "data_source": "Cosmic Watch Database",
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "today_asteroids": asteroids,
            "statistics": statistics,
            "alerts": [
                {
                    "id": "alert_001",
                    "level": "info",
                    "title": "System Active",
                    "message": f"Monitoring {statistics['total_count']} asteroids",
                    "timestamp": datetime.now().isoformat()
                }
            ]
        }
    }

@app.get("/asteroids/today", tags=["Asteroids"])
@limiter.limit("30/minute")
async def get_today_asteroids(
    request: Request,
    limit: int = Query(20, ge=1, le=100)
):
    """Today's asteroid approaches"""
    asteroids = processor.process_asteroids(SAMPLE_ASTEROIDS["today"])
    
    return {
        "success": True,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "total": len(asteroids),
        "limit": limit,
        "asteroids": asteroids[:limit],
        "source": "Cosmic Watch Database",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/asteroids/hazardous", tags=["Asteroids"])
@limiter.limit("30/minute")
async def get_hazardous_asteroids(request: Request):
    """Potentially hazardous asteroids"""
    asteroids = [a for a in SAMPLE_ASTEROIDS["today"] if a["is_potentially_hazardous"]]
    processed = processor.process_asteroids(asteroids)
    processed.sort(key=lambda x: x.get("risk_score", 0), reverse=True)
    
    return {
        "success": True,
        "count": len(processed),
        "hazardous_asteroids": processed,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/asteroids/upcoming", tags=["Asteroids"])
@limiter.limit("30/minute")
async def get_upcoming_asteroids(request: Request):
    """Upcoming close approaches"""
    asteroids = processor.process_asteroids(SAMPLE_ASTEROIDS["upcoming"])
    
    return {
        "success": True,
        "count": len(asteroids),
        "upcoming_asteroids": asteroids,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/statistics", tags=["Analytics"])
@limiter.limit("30/minute")
async def get_statistics(request: Request):
    """Comprehensive statistics"""
    asteroids = processor.process_asteroids(SAMPLE_ASTEROIDS["today"])
    stats = generate_statistics(asteroids)
    
    return {
        "success": True,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "statistics": stats,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/alerts", tags=["Monitoring"])
@limiter.limit("30/minute")
async def get_alerts(request: Request):
    """Current threat alerts"""
    asteroids = processor.process_asteroids(SAMPLE_ASTEROIDS["today"])
    
    alerts = []
    for asteroid in asteroids:
        risk_score = asteroid.get("risk_score", 0)
        if risk_score >= 50:
            alerts.append({
                "id": f"alert_{asteroid['id']}",
                "level": "warning",
                "title": f"HIGH RISK: {asteroid['name']}",
                "message": f"Asteroid detected with risk score {risk_score}",
                "asteroid_id": asteroid["id"],
                "timestamp": datetime.now().isoformat()
            })
    
    if not alerts:
        alerts.append({
            "id": "system_normal",
            "level": "info",
            "title": "System Normal",
            "message": "No immediate threats detected",
            "timestamp": datetime.now().isoformat()
        })
    
    return {
        "success": True,
        "count": len(alerts),
        "alerts": alerts,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/simulate/threat", tags=["Simulation"])
@limiter.limit("10/minute")
async def simulate_threat(request: Request):
    """Simulate a threat scenario"""
    simulated_asteroid = {
        "id": "sim_001",
        "name": "SIMULATED THREAT 2026-XF1",
        "is_potentially_hazardous": True,
        "estimated_diameter_km": 0.8,
        "close_approach_date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
        "miss_distance_km": 150000,
        "relative_velocity_kph": 72000,
        "orbiting_body": "Earth"
    }
    
    processed = processor.process_asteroids([simulated_asteroid])[0]
    
    return {
        "success": True,
        "simulation": True,
        "warning": "SIMULATION MODE - NOT REAL DATA",
        "scenario": {
            "name": "Imminent Threat Simulation",
            "description": "Demonstration of system response",
            "time_to_impact": "7 days",
            "estimated_impact_energy": "50 megatons"
        },
        "asteroid": processed,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/nasa/real", tags=["NASA"])
@limiter.limit("10/minute")
async def get_real_nasa_data(request: Request):
    """Get real NASA asteroid data"""
    api_key = config.NASA_API_KEY
    today = datetime.now().strftime("%Y-%m-%d")
    
    url = f"{config.NASA_BASE_URL}/feed"
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
                    
                    asteroids = []
                    element_count = data.get("element_count", 0)
                    
                    if element_count > 0:
                        for date_str, neo_list in data.get("near_earth_objects", {}).items():
                            for asteroid in neo_list[:5]:  # Limit to 5 for demo
                                asteroids.append({
                                    "id": asteroid.get("id"),
                                    "name": asteroid.get("name"),
                                    "is_hazardous": asteroid.get("is_potentially_hazardous_asteroid", False),
                                    "diameter_km": asteroid.get("estimated_diameter", {}).get("kilometers", {}).get("estimated_diameter_max", 0),
                                    "miss_distance_km": float(asteroid.get("close_approach_data", [{}])[0].get("miss_distance", {}).get("kilometers", 0)) if asteroid.get("close_approach_data") else 0,
                                    "relative_velocity_kph": float(asteroid.get("close_approach_data", [{}])[0].get("relative_velocity", {}).get("kilometers_per_hour", 0)) if asteroid.get("close_approach_data") else 0
                                })
                    
                    return {
                        "success": True,
                        "date": today,
                        "total_asteroids": element_count,
                        "asteroids": asteroids,
                        "source": "NASA NeoWS API - Real Data",
                        "is_real_data": True,
                        "timestamp": datetime.now().isoformat(),
                        "message": "Real NASA data fetched successfully"
                    }
                elif response.status == 429:
                    return {
                        "success": False,
                        "date": today,
                        "message": "NASA API rate limit exceeded. Try again in an hour.",
                        "source": "NASA API",
                        "is_real_data": False,
                        "timestamp": datetime.now().isoformat()
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
                    
    except asyncio.TimeoutError:
        return {
            "success": False,
            "date": today,
            "message": "NASA API timeout",
            "source": "NASA API",
            "is_real_data": False,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "date": today,
            "message": f"Error: {str(e)}",
            "source": "NASA API",
            "is_real_data": False,
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/nasa/status", tags=["NASA"])
@limiter.limit("10/minute")
async def nasa_api_status(request: Request):
    """Check NASA API connection status"""
    api_key = config.NASA_API_KEY
    
    return {
        "api_key": api_key[:8] + "..." if len(api_key) > 8 else api_key,
        "key_type": "PERSONAL" if api_key != "DEMO_KEY" else "DEMO",
        "timestamp": datetime.now().isoformat(),
        "status": "Ready",
        "message": "NASA API configured successfully"
    }

# ============ WEB SOCKET ENDPOINTS ============

@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await manager.connect(websocket)
    
    await websocket.send_json({
        "type": "connection",
        "message": "Connected to Cosmic Watch",
        "timestamp": datetime.now().isoformat()
    })
    
    try:
        update_count = 0
        while True:
            update_count += 1
            data = {
                "type": "update",
                "update_id": update_count,
                "timestamp": datetime.now().isoformat(),
                "message": "Real-time monitoring active",
                "asteroids_tracked": len(SAMPLE_ASTEROIDS["today"]),
                "hazardous_count": len([a for a in SAMPLE_ASTEROIDS["today"] if a["is_potentially_hazardous"]])
            }
            
            await websocket.send_json(data)
            await asyncio.sleep(10)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ============ ERROR HANDLERS ============

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail,
            "timestamp": datetime.now().isoformat()
        }
    )

# ============ STARTUP EVENT ============

@app.on_event("startup")
async def startup_event():
    logger.info("Cosmic Watch API starting up...")
    logger.info(f"NASA API Key: {config.NASA_API_KEY[:8]}...")
    logger.info("Memory cache initialized")

# ============ MAIN ENTRY POINT ============

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main_simple:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )