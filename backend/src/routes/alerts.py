from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
from uuid import UUID

from ..database import get_db
from .. import schemas, crud, auth
from ..rate_limiter import alert_rate_limit

router = APIRouter(prefix="/alerts", tags=["alerts"])
logger = logging.getLogger(__name__)

@router.post("", response_model=schemas.AlertResponse)
@alert_rate_limit
async def create_alert(
    alert_data: schemas.AlertCreate,
    current_user: schemas.TokenData = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new asteroid alert"""
    try:
        # Verify asteroid exists or fetch from NASA
        asteroid = crud.AsteroidCRUD.get_asteroid(db, alert_data.asteroid_id)
        
        if not asteroid:
            # Asteroid not in database, we should fetch or validate it exists
            # For now, we'll allow creation with just the ID
            pass
        
        # Check if user already has an alert for this asteroid
        existing_alerts = crud.AlertCRUD.get_user_alerts(db, current_user.user_id)
        for alert in existing_alerts:
            if alert.asteroid_id == alert_data.asteroid_id and alert.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Alert already exists for asteroid {alert_data.asteroid_id}"
                )
        
        # Create alert
        alert = crud.AlertCRUD.create_alert(db, alert_data, current_user.user_id)
        
        return alert
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create alert: {str(e)}"
        )

@router.get("", response_model=List[schemas.AlertResponse])
async def get_user_alerts(
    active_only: bool = Query(True, description="Return only active alerts"),
    current_user: schemas.TokenData = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get all alerts for the current user"""
    try:
        if active_only:
            alerts = crud.AlertCRUD.get_active_alerts(db, current_user.user_id)
        else:
            alerts = crud.AlertCRUD.get_user_alerts(db, current_user.user_id)
        
        return alerts
        
    except Exception as e:
        logger.error(f"Error fetching alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch alerts: {str(e)}"
        )

@router.get("/{alert_id}", response_model=schemas.AlertResponse)
async def get_alert(
    alert_id: UUID,
    current_user: schemas.TokenData = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get specific alert by ID"""
    try:
        alert = crud.AlertCRUD.get_alert(db, alert_id)
        
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        # Check ownership
        if alert.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this alert"
            )
        
        return alert
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch alert: {str(e)}"
        )

@router.put("/{alert_id}", response_model=schemas.AlertResponse)
async def update_alert(
    alert_id: UUID,
    alert_update: schemas.AlertUpdate,
    current_user: schemas.TokenData = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Update an existing alert"""
    try:
        alert = crud.AlertCRUD.get_alert(db, alert_id)
        
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        # Check ownership
        if alert.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this alert"
            )
        
        updated_alert = crud.AlertCRUD.update_alert(db, alert_id, alert_update)
        
        if not updated_alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found during update"
            )
        
        return updated_alert
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update alert: {str(e)}"
        )

@router.delete("/{alert_id}")
async def delete_alert(
    alert_id: UUID,
    current_user: schemas.TokenData = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an alert"""
    try:
        alert = crud.AlertCRUD.get_alert(db, alert_id)
        
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        # Check ownership
        if alert.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this alert"
            )
        
        success = crud.AlertCRUD.delete_alert(db, alert_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete alert"
            )
        
        return {"message": "Alert deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete alert: {str(e)}"
        )

@router.post("/{alert_id}/trigger")
async def trigger_alert_test(
    alert_id: UUID,
    current_user: schemas.TokenData = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Test trigger an alert (for testing purposes)"""
    try:
        alert = crud.AlertCRUD.get_alert(db, alert_id)
        
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert not found"
            )
        
        # Check ownership
        if alert.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to trigger this alert"
            )
        
        success = crud.AlertCRUD.trigger_alert(db, alert_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to trigger alert"
            )
        
        return {
            "message": "Alert triggered successfully",
            "alert_id": alert_id,
            "triggered_at": alert.last_triggered.isoformat() if alert.last_triggered else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger alert: {str(e)}"
        )

@router.get("/check/upcoming")
async def check_upcoming_alerts(
    days: int = Query(7, ge=1, le=30, description="Days to check ahead"),
    current_user: schemas.TokenData = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Check which alerts might be triggered in the coming days"""
    try:
        # Get user's active alerts
        alerts = crud.AlertCRUD.get_active_alerts(db, current_user.user_id)
        
        if not alerts:
            return {
                "message": "No active alerts found",
                "alerts_checked": 0,
                "potential_triggers": []
            }
        
        # Get upcoming asteroids
        upcoming = crud.AsteroidCRUD.get_upcoming_approaches(db, days)
        
        potential_triggers = []
        
        for alert in alerts:
            for asteroid in upcoming:
                if asteroid.id == alert.asteroid_id:
                    # Check if alert criteria are met
                    if (asteroid.miss_distance_km <= alert.threshold_distance_km or
                        asteroid.risk_score >= alert.threshold_risk_score):
                        
                        potential_triggers.append({
                            "alert_id": alert.id,
                            "alert_name": alert.name,
                            "asteroid_id": asteroid.id,
                            "asteroid_name": asteroid.name,
                            "close_approach_date": asteroid.close_approach_date,
                            "miss_distance_km": asteroid.miss_distance_km,
                            "threshold_distance_km": alert.threshold_distance_km,
                            "risk_score": asteroid.risk_score,
                            "threshold_risk_score": alert.threshold_risk_score,
                            "days_until": (asteroid.close_approach_date - datetime.now()).days if asteroid.close_approach_date else None
                        })
        
        return {
            "alerts_checked": len(alerts),
            "asteroids_checked": len(upcoming),
            "potential_triggers": potential_triggers,
            "check_period_days": days,
            "checked_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error checking upcoming alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check upcoming alerts: {str(e)}"
        )