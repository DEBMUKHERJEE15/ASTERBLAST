from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
import re

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    is_researcher: bool = False

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "username": "astronomer1",
                "password": "SecurePass123!",
                "is_researcher": False
            }
        }

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int

class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None

# Asteroid schemas
class AsteroidBase(BaseModel):
    id: str
    name: str
    is_potentially_hazardous: bool
    estimated_diameter_km: float
    miss_distance_km: float
    relative_velocity_kph: float
    risk_score: float
    threat_level: str

class AsteroidResponse(AsteroidBase):
    close_approach_date: str
    absolute_magnitude: Optional[float] = None
    orbiting_body: str = "Earth"
    size_category: str
    distance_category: str
    
    class Config:
        from_attributes = True

# Watched asteroid schemas
class WatchedAsteroidCreate(BaseModel):
    asteroid_id: str
    asteroid_name: str
    notes: Optional[str] = None

class WatchedAsteroidResponse(BaseModel):
    asteroid_id: str
    asteroid_name: str
    notes: Optional[str] = None
    added_at: datetime

# Alert schemas
class AlertCreate(BaseModel):
    asteroid_id: str
    name: str
    threshold_distance_km: float = Field(..., gt=0)
    threshold_risk_score: float = Field(..., ge=0, le=100)

class AlertResponse(BaseModel):
    id: int
    asteroid_id: str
    name: str
    threshold_distance_km: float
    threshold_risk_score: float
    notification_method: str
    is_active: bool
    created_at: datetime