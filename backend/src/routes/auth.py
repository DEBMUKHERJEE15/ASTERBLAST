from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import logging
from typing import Dict, Any

from ..database import get_db
from .. import schemas, crud, auth
from ..config import settings
from ..rate_limiter import login_rate_limit, register_rate_limit

router = APIRouter(prefix="/auth", tags=["authentication"])
logger = logging.getLogger(__name__)

@router.post("/register", response_model=Dict[str, Any])
@register_rate_limit
async def register(
    user_data: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    """Register new user"""
    try:
        # Check if user exists
        if crud.UserCRUD.get_user_by_email(db, user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        if crud.UserCRUD.get_user_by_username(db, user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # Hash password
        hashed_password = auth.get_password_hash(user_data.password)
        
        # Create user
        db_user = crud.UserCRUD.create_user(db, schemas.UserCreate(
            email=user_data.email,
            username=user_data.username,
            password=hashed_password,
            is_researcher=user_data.is_researcher
        ))
        
        # Create tokens
        access_token = auth.create_access_token(
            data={"sub": str(db_user.id), "email": db_user.email}
        )
        
        refresh_token = auth.create_refresh_token(
            data={"sub": str(db_user.id), "email": db_user.email}
        )
        
        return {
            "message": "User registered successfully",
            "user": {
                "id": db_user.id,
                "email": db_user.email,
                "username": db_user.username,
                "is_researcher": db_user.is_researcher,
                "created_at": db_user.created_at
            },
            "tokens": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during registration"
        )

@router.post("/login", response_model=Dict[str, Any])
@login_rate_limit
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login user and get access token"""
    try:
        # Find user
        user = crud.UserCRUD.get_user_by_email(db, form_data.username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Verify password
        if not auth.verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated"
            )
        
        # Create tokens
        access_token = auth.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        
        refresh_token = auth.create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )
        
        return {
            "message": "Login successful",
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "is_researcher": user.is_researcher,
                "created_at": user.created_at
            },
            "tokens": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login"
        )

@router.post("/refresh", response_model=Dict[str, Any])
async def refresh_token(
    refresh_token: str
):
    """Refresh access token using refresh token"""
    try:
        new_access_token = auth.refresh_access_token(refresh_token)
        
        if not new_access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during token refresh"
        )

@router.post("/logout")
async def logout(
    current_user: schemas.TokenData = Depends(auth.get_current_user)
):
    """Logout user (client should discard tokens)"""
    # In a real implementation, you might want to blacklist the token
    return {"message": "Logout successful"}

@router.get("/me", response_model=schemas.UserResponse)
async def get_current_user_info(
    current_user: schemas.TokenData = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user information"""
    try:
        user = crud.UserCRUD.get_user(db, current_user.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user info error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )