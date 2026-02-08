from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime

from . import models, schemas
from .auth import get_password_hash

# User CRUD operations
class UserCRUD:
    @staticmethod
    def get_user(db: Session, user_id: int) -> Optional[models.User]:
        """Get user by ID"""
        return db.query(models.User).filter(models.User.id == user_id).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
        """Get user by email"""
        return db.query(models.User).filter(models.User.email == email).first()
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
        """Get user by username"""
        return db.query(models.User).filter(models.User.username == username).first()
    
    @staticmethod
    def create_user(db: Session, user: schemas.UserCreate) -> models.User:
        """Create new user"""
        db_user = models.User(
            email=user.email,
            username=user.username,
            hashed_password=get_password_hash(user.password),
            is_researcher=user.is_researcher
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

# Asteroid CRUD operations (simplified for demo)
class AsteroidCRUD:
    @staticmethod
    def get_hazardous_asteroids(db: Session) -> List[models.Asteroid]:
        """Get hazardous asteroids"""
        return []

# Alert CRUD operations (simplified for demo)
class AlertCRUD:
    @staticmethod
    def get_user_alerts(db: Session, user_id: int) -> List[models.Alert]:
        """Get user alerts"""
        return []

# Chat CRUD operations (simplified for demo)
class ChatCRUD:
    @staticmethod
    def create_message(db: Session, user_id: int, message: str, room_id: str) -> models.ChatMessage:
        """Create chat message"""
        db_message = models.ChatMessage(
            user_id=user_id,
            room_id=room_id,
            message=message
        )
        db.add(db_message)
        db.commit()
        db.refresh(db_message)
        return db_message