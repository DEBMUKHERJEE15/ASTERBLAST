#!/usr/bin/env python3
"""
🌌 COSMIC WATCH - Asteroid Threat Detection System
Enhanced with monitoring and better error handling
"""

import os
import sys
import uvicorn
import psutil
from datetime import datetime

def print_system_info():
    """Print system information"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    
    print("📊 System Information:")
    print(f"   CPU Usage: {cpu_percent}%")
    print(f"   Memory: {memory.percent}% used ({memory.used / 1024 / 1024:.1f} MB)")
    print(f"   Available Memory: {memory.available / 1024 / 1024:.1f} MB")

def check_dependencies():
    """Check if all dependencies are available"""
    try:
        import fastapi
        import uvicorn
        import aiohttp
        import sqlalchemy
        import redis
        print("✅ All dependencies are available")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return False

def main():
    """Main entry point"""
    # Banner
    banner = r"""
     ____                 _     __        __      ____    _       _     
    / ___|   ___    ___  (_)   /\ \      / /     / ___|  | |__   | |__  
    \___ \  / __|  / __| | |   \ \ \ /\ / /     | |      | '_ \  | '_ \ 
     ___) | \__ \ | (__  | |    \ \ V  V /      | |___   | | | | | |_) |
    |____/  |___/  \___| |_|     \_\_/\_/        \____|  |_| |_| |_.__/ 
    
    ╔══════════════════════════════════════════════════════════════╗
    ║                    REAL-TIME ASTEROID WATCH                  ║
    ║                Threat Detection & Analysis System            ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)
    
    print("🚀 Starting Cosmic Watch API...")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Check dependencies
    if not check_dependencies():
        print("\n⚠️  Some dependencies are missing. Please run:")
        print("   pip install -r requirements.txt")
        sys.exit(1)
    
    # System info
    print_system_info()
    print("=" * 60)
    
    # Check environment
    env = os.getenv("ENVIRONMENT", "development")
    print(f"📁 Environment: {env}")
    print(f"🔧 Debug mode: {'enabled' if env == 'development' else 'disabled'}")
    
    # Check NASA API key
    nasa_key = os.getenv("NASA_API_KEY", "DEMO_KEY")
    if nasa_key == "DEMO_KEY":
        print("⚠️  Using NASA DEMO_KEY (30 req/hour limit)")
        print("💡 Get personal key: https://api.nasa.gov/#signUp")
    else:
        print(f"✅ Using personal NASA API key: {nasa_key[:8]}...")
    
    print("=" * 60)
    
    print("📋 Available endpoints:")
    print("  • 🌐 Main Dashboard: http://localhost:8000/dashboard")
    print("  • 📚 Documentation: http://localhost:8000/docs")
    print("  • 📊 Today's Asteroids: http://localhost:8000/asteroids/today")
    print("  • ⚠️ Hazardous Asteroids: http://localhost:8000/asteroids/hazardous")
    print("  • 📅 Upcoming Threats: http://localhost:8000/asteroids/upcoming")
    print("  • 📈 Statistics: http://localhost:8000/statistics")
    print("  • 🚨 Alerts: http://localhost:8000/alerts")
    print("  • 🎯 Threat Simulation: http://localhost:8000/simulate/threat")
    print("  • 🛰️ Real NASA Data: http://localhost:8000/api/nasa/real")
    print("  • 🏥 Health Check: http://localhost:8000/health")
    print("=" * 60)
    
    print("🔧 Features enabled:")
    print("  • Rate limiting (60 req/min)")
    print("  • Real-time WebSocket updates")
    print("  • NASA API integration")
    print("  • User authentication")
    print("  • Redis caching")
    print("  • PostgreSQL support")
    print("=" * 60)
    
    # Start server with enhanced configuration
    config = uvicorn.Config(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=env == "development",
        log_level="info",
        access_log=True,
        workers=1 if env == "development" else 4,
        proxy_headers=True,
        forwarded_allow_ips="*"
    )
    
    server = uvicorn.Server(config)
    
    try:
        server.run()
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down Cosmic Watch...")
        print("👋 Thank you for using our system!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8001, reload=True)