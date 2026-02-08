import json
from datetime import datetime

collection = {
    "info": {
        "name": "Cosmic Watch API",
        "description": f"Postman Collection for Cosmic Watch - Generated {datetime.now().strftime('%Y-%m-%d')}",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    },
    "item": [
        {
            "name": "🚀 Welcome",
            "item": [
                {
                    "name": "Root Endpoint",
                    "request": {
                        "method": "GET",
                        "header": [],
                        "url": {
                            "raw": "{{base_url}}/",
                            "host": ["{{base_url}}"],
                            "path": ["/"]
                        },
                        "description": "Get API information and available endpoints"
                    },
                    "response": []
                },
                {
                    "name": "Health Check",
                    "request": {
                        "method": "GET",
                        "header": [],
                        "url": {
                            "raw": "{{base_url}}/health",
                            "host": ["{{base_url}}"],
                            "path": ["health"]
                        },
                        "description": "Check system health and status"
                    },
                    "response": []
                }
            ]
        },
        {
            "name": "📊 Dashboard & Analytics",
            "item": [
                {
                    "name": "Dashboard",
                    "request": {
                        "method": "GET",
                        "header": [],
                        "url": {
                            "raw": "{{base_url}}/dashboard",
                            "host": ["{{base_url}}"],
                            "path": ["dashboard"]
                        },
                        "description": "Get comprehensive dashboard data"
                    }
                },
                {
                    "name": "Statistics",
                    "request": {
                        "method": "GET",
                        "header": [],
                        "url": {
                            "raw": "{{base_url}}/statistics",
                            "host": ["{{base_url}}"],
                            "path": ["statistics"]
                        },
                        "description": "Get detailed asteroid statistics"
                    }
                }
            ]
        },
        {
            "name": "🪐 Asteroid Data",
            "item": [
                {
                    "name": "Today's Asteroids",
                    "request": {
                        "method": "GET",
                        "header": [],
                        "url": {
                            "raw": "{{base_url}}/asteroids/today?limit=10",
                            "host": ["{{base_url}}"],
                            "path": ["asteroids", "today"],
                            "query": [
                                {"key": "limit", "value": "10"}
                            ]
                        },
                        "description": "Get today's asteroid approaches"
                    }
                },
                {
                    "name": "Hazardous Asteroids",
                    "request": {
                        "method": "GET",
                        "header": [],
                        "url": {
                            "raw": "{{base_url}}/asteroids/hazardous",
                            "host": ["{{base_url}}"],
                            "path": ["asteroids", "hazardous"]
                        },
                        "description": "Get potentially hazardous asteroids"
                    }
                },
                {
                    "name": "Upcoming Asteroids",
                    "request": {
                        "method": "GET",
                        "header": [],
                        "url": {
                            "raw": "{{base_url}}/asteroids/upcoming",
                            "host": ["{{base_url}}"],
                            "path": ["asteroids", "upcoming"]
                        },
                        "description": "Get upcoming close approaches"
                    }
                }
            ]
        },
        {
            "name": "🛰️ NASA Integration",
            "item": [
                {
                    "name": "Real NASA Data",
                    "request": {
                        "method": "GET",
                        "header": [],
                        "url": {
                            "raw": "{{base_url}}/api/nasa/real",
                            "host": ["{{base_url}}"],
                            "path": ["api", "nasa", "real"]
                        },
                        "description": "Fetch real data from NASA API"
                    }
                },
                {
                    "name": "NASA API Status",
                    "request": {
                        "method": "GET",
                        "header": [],
                        "url": {
                            "raw": "{{base_url}}/api/nasa/status",
                            "host": ["{{base_url}}"],
                            "path": ["api", "nasa", "status"]
                        },
                        "description": "Check NASA API connection status"
                    }
                }
            ]
        },
        {
            "name": "🎯 Simulation & Analysis",
            "item": [
                {
                    "name": "Threat Simulation",
                    "request": {
                        "method": "GET",
                        "header": [],
                        "url": {
                            "raw": "{{base_url}}/simulate/threat",
                            "host": ["{{base_url}}"],
                            "path": ["simulate", "threat"]
                        },
                        "description": "Simulate threat scenario (impressive demo)"
                    }
                }
            ]
        },
        {
            "name": "🚨 Monitoring",
            "item": [
                {
                    "name": "Alerts",
                    "request": {
                        "method": "GET",
                        "header": [],
                        "url": {
                            "raw": "{{base_url}}/alerts",
                            "host": ["{{base_url}}"],
                            "path": ["alerts"]
                        },
                        "description": "Get current threat alerts"
                    }
                }
            ]
        }
    ],
    "event": [
        {
            "listen": "test",
            "script": {
                "type": "text/javascript",
                "exec": [
                    "pm.test('Status code is 200', function () {",
                    "    pm.response.to.have.status(200);",
                    "});",
                    "",
                    "pm.test('Response time is acceptable', function () {",
                    "    pm.expect(pm.response.responseTime).to.be.below(1000);",
                    "});"
                ]
            }
        }
    ],
    "variable": [
        {
            "key": "base_url",
            "value": "http://localhost:8001"
        }
    ]
}

# Save collection
with open('Cosmic_Watch.postman_collection.json', 'w') as f:
    json.dump(collection, f, indent=2)

print("✅ Postman collection created: Cosmic_Watch.postman_collection.json")
print("📁 Import this file into Postman to test all endpoints")