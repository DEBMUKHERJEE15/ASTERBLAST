from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Generator, Optional
import logging

from .database import SessionLocal
from .auth import get_current_user
from .schemas import TokenData

logger = logging.getLogger(__name__)

def get_db() -> Generator:
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_active_user(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> TokenData:
    """Get current active user"""
    # In a real implementation, check if user exists and is active
    return current_user

def get_admin_user(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> TokenData:
    """Get admin user (for admin-only endpoints)"""
    # In a real implementation, check if user is admin
    # For now, return the current user
    return current_user