import os
import sys
import json
import logging
import math
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

import aiohttp
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psutil

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="🌌 Cosmic Watch API", version="1.0.0")

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ SAMPLE DATA ============
SAMPLE_ASTEROIDS = [
    {
        "id": "3542519",
        "name": "(2010 PK9)",
        "is_potentially_hazardous": True,
        "estimated_diameter_km": 0.284,
        "miss_distance_km": 7230000,
        "relative_velocity_kph": 67600,
        "close_approach_date": datetime.now().strftime("%Y-%m-%d")
    },
    {
        "id": "3726710",
        "name": "(2015 RC)",
        "is_potentially_hazardous": False,
        "estimated_diameter_km": 0.041,
        "miss_distance_km": 15400000,
        "relative_velocity_kph": 54200,
        "close_approach_date": datetime.now().strftime("%Y-%m-%d")
    }
]

# ============ RISK CALCULATOR ============
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
    
    return min(100, round(score, 1))

def get_threat_level(score: float) -> str:
    if score >= 70:
        return "CRITICAL"
    elif score >= 50:
        return "HIGH"
    elif score >= 30:
        return "MODERATE"
    elif score >= 10:
        return "LOW"
    else:
        return "MINIMAL"

# ============ API ENDPOINTS ============
@app.get("/")
async def root():
    return {
        "app": "COSMIC WATCH",
        "version": "1.0.0",
        "status": "OPERATIONAL",
        "timestamp": datetime.now().isoformat(),
        "endpoints": [
            "/health",
            "/dashboard",
            "/asteroids/today",
            "/asteroids/hazardous",
            "/statistics",
            "/alerts"
        ]
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent
    }

@app.get("/dashboard")
async def dashboard():
    asteroids = []
    for asteroid in SAMPLE_ASTEROIDS:
        risk_score = calculate_risk_score(asteroid)
        threat_level = get_threat_level(risk_score)
        
        asteroids.append({
            **asteroid,
            "risk_score": risk_score,
            "threat_level": threat_level
        })
    
    hazardous = len([a for a in asteroids if a["is_potentially_hazardous"]])
    
    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "total_asteroids": len(asteroids),
        "hazardous_count": hazardous,
        "asteroids": asteroids
    }

@app.get("/asteroids/today")
async def asteroids_today():
    asteroids = []
    for asteroid in SAMPLE_ASTEROIDS:
        risk_score = calculate_risk_score(asteroid)
        threat_level = get_threat_level(risk_score)
        
        asteroids.append({
            **asteroid,
            "risk_score": risk_score,
            "threat_level": threat_level
        })
    
    return {
        "success": True,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "total": len(asteroids),
        "asteroids": asteroids
    }

@app.get("/asteroids/hazardous")
async def hazardous_asteroids():
    hazardous = [a for a in SAMPLE_ASTEROIDS if a["is_potentially_hazardous"]]
    processed = []
    
    for asteroid in hazardous:
        risk_score = calculate_risk_score(asteroid)
        threat_level = get_threat_level(risk_score)
        
        processed.append({
            **asteroid,
            "risk_score": risk_score,
            "threat_level": threat_level
        })
    
    return {
        "success": True,
        "count": len(processed),
        "asteroids": processed
    }

@app.get("/statistics")
async def statistics():
    asteroids = SAMPLE_ASTEROIDS
    hazardous = len([a for a in asteroids if a["is_potentially_hazardous"]])
    
    return {
        "success": True,
        "total_count": len(asteroids),
        "hazardous_count": hazardous,
        "hazardous_percentage": round((hazardous / len(asteroids)) * 100, 1) if asteroids else 0
    }

@app.get("/alerts")
async def alerts():
    alerts_list = []
    
    for asteroid in SAMPLE_ASTEROIDS:
        if asteroid["is_potentially_hazardous"]:
            alerts_list.append({
                "id": f"alert_{asteroid['id']}",
                "level": "warning",
                "title": f"Hazardous Asteroid: {asteroid['name']}",
                "message": f"Potentially hazardous asteroid detected",
                "timestamp": datetime.now().isoformat()
            })
    
    if not alerts_list:
        alerts_list.append({
            "id": "system_normal",
            "level": "info",
            "title": "System Normal",
            "message": "No immediate threats detected",
            "timestamp": datetime.now().isoformat()
        })
    
    return {
        "success": True,
        "count": len(alerts_list),
        "alerts": alerts_list
    }

# WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

manager = ConnectionManager()

@app.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    
    await websocket.send_json({
        "type": "connection",
        "message": "Connected to Cosmic Watch",
        "timestamp": datetime.now().isoformat()
    })
    
    try:
        while True:
            # Send periodic updates
            await websocket.send_json({
                "type": "update",
                "timestamp": datetime.now().isoformat(),
                "message": "Monitoring active",
                "asteroids_tracked": len(SAMPLE_ASTEROIDS)
            })
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Startup event
@app.on_event("startup")
async def startup_event():
    logger.info("🌌 Cosmic Watch API started on http://localhost:8000")
    logger.info("📚 Documentation: http://localhost:8000/docs")

# Run the app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)