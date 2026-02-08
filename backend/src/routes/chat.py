from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from uuid import UUID

from ..database import get_db
from .. import schemas, crud, auth
from ..rate_limiter import chat_rate_limit

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger(__name__)

@router.get("/rooms", response_model=List[str])
async def get_chat_rooms(
    current_user: schemas.TokenData = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get available chat rooms"""
    try:
        # Get recent rooms for the user
        rooms = crud.ChatCRUD.get_recent_rooms(db, current_user.user_id)
        
        # Add general room if not present
        if "general" not in rooms:
            rooms.insert(0, "general")
        
        # Add asteroid rooms the user has alerts for
        alerts = crud.AlertCRUD.get_active_alerts(db, current_user.user_id)
        asteroid_rooms = [f"asteroid_{alert.asteroid_id}" for alert in alerts]
        
        # Combine and deduplicate
        all_rooms = list(set(rooms + asteroid_rooms))
        
        return all_rooms
        
    except Exception as e:
        logger.error(f"Error fetching chat rooms: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch chat rooms: {str(e)}"
        )

@router.get("/messages/{room_id}", response_model=List[schemas.ChatMessageResponse])
async def get_room_messages(
    room_id: str,
    skip: int = Query(0, ge=0, description="Number of messages to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum messages to return"),
    current_user: schemas.TokenData = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get messages from a chat room"""
    try:
        messages = crud.ChatCRUD.get_room_messages(db, room_id, skip, limit)
        
        # Convert to response format
        response_messages = []
        for message in messages:
            user = crud.UserCRUD.get_user(db, message.user_id)
            response_messages.append(schemas.ChatMessageResponse(
                id=message.id,
                user_id=message.user_id,
                username=user.username if user else "Unknown",
                message=message.message,
                room_id=message.room_id,
                is_system_message=message.is_system_message,
                created_at=message.created_at
            ))
        
        return response_messages
        
    except Exception as e:
        logger.error(f"Error fetching room messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch room messages: {str(e)}"
        )

@router.post("/messages", response_model=schemas.ChatMessageResponse)
@chat_rate_limit
async def send_message(
    message_data: schemas.ChatMessageCreate,
    current_user: schemas.TokenData = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Send a chat message"""
    try:
        # Create message
        message = crud.ChatCRUD.create_message(
            db, 
            current_user.user_id, 
            message_data.message, 
            message_data.room_id
        )
        
        # Get user info for response
        user = crud.UserCRUD.get_user(db, current_user.user_id)
        
        return schemas.ChatMessageResponse(
            id=message.id,
            user_id=message.user_id,
            username=user.username if user else "Unknown",
            message=message.message,
            room_id=message.room_id,
            is_system_message=message.is_system_message,
            created_at=message.created_at
        )
        
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )

@router.get("/asteroid/{asteroid_id}/messages", response_model=List[schemas.ChatMessageResponse])
async def get_asteroid_chat(
    asteroid_id: str,
    skip: int = Query(0, ge=0, description="Number of messages to skip"),
    limit: int = Query(100, ge=1, le=500, description="Maximum messages to return"),
    current_user: schemas.TokenData = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get chat messages for a specific asteroid"""
    try:
        room_id = f"asteroid_{asteroid_id}"
        return await get_room_messages(room_id, skip, limit, current_user, db)
        
    except Exception as e:
        logger.error(f"Error fetching asteroid chat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch asteroid chat: {str(e)}"
        )

@router.post("/asteroid/{asteroid_id}/messages", response_model=schemas.ChatMessageResponse)
async def send_asteroid_message(
    asteroid_id: str,
    message: str = Query(..., min_length=1, max_length=1000, description="Message content"),
    current_user: schemas.TokenData = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Send a message to an asteroid-specific chat room"""
    try:
        room_id = f"asteroid_{asteroid_id}"
        message_data = schemas.ChatMessageCreate(message=message, room_id=room_id)
        return await send_message(message_data, current_user, db)
        
    except Exception as e:
        logger.error(f"Error sending asteroid message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send asteroid message: {str(e)}"
        )