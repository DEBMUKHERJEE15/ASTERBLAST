from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from ..database import get_db
from .. import schemas, crud, auth
from ..neo_fetcher import get_nasa_fetcher
from ..rate_limiter import feed_rate_limit, asteroid_rate_limit, search_rate_limit

router = APIRouter(prefix="/asteroids", tags=["asteroids"])
logger = logging.getLogger(__name__)

@router.get("/feed", response_model=Dict[str, Any])
@feed_rate_limit
async def get_asteroid_feed(
    days: int = Query(7, ge=1, le=30, description="Number of days to fetch"),
    hazardous_only: bool = Query(False, description="Filter only hazardous asteroids"),
    min_diameter_km: Optional[float] = Query(None, ge=0, description="Minimum diameter in km"),
    max_distance_km: Optional[float] = Query(None, ge=0, description="Maximum miss distance in km"),
    min_risk_score: Optional[float] = Query(None, ge=0, le=100, description="Minimum risk score"),
    max_risk_score: Optional[float] = Query(None, ge=0, le=100, description="Maximum risk score"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: schemas.TokenData = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get asteroid feed with filtering and pagination"""
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Fetch from NASA
        fetcher = await get_nasa_fetcher()
        data = await fetcher.fetch_feed(
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
        
        asteroids = data.get("asteroids", [])
        
        # Apply filters
        filtered_asteroids = []
        for asteroid in asteroids:
            # Hazardous filter
            if hazardous_only and not asteroid["is_potentially_hazardous"]:
                continue
            
            # Diameter filter
            if min_diameter_km is not None:
                try:
                    diameter = asteroid["estimated_diameter"]["kilometers"]["estimated_diameter_max"]
                    if diameter < min_diameter_km:
                        continue
                except (KeyError, ValueError):
                    continue
            
            # Distance filter
            if max_distance_km is not None and asteroid.get("close_approach_data"):
                try:
                    distance = float(asteroid["close_approach_data"][0]["miss_distance"]["kilometers"])
                    if distance > max_distance_km:
                        continue
                except (KeyError, ValueError):
                    continue
            
            # Risk score filter
            risk_score = asteroid.get("risk_score", 0)
            if min_risk_score is not None and risk_score < min_risk_score:
                continue
            if max_risk_score is not None and risk_score > max_risk_score:
                continue
            
            filtered_asteroids.append(asteroid)
        
        # Pagination
        total = len(filtered_asteroids)
        start_idx = (page - 1) * size
        end_idx = start_idx + size
        paginated_asteroids = filtered_asteroids[start_idx:end_idx]
        
        return {
            "data": paginated_asteroids,
            "pagination": {
                "total": total,
                "page": page,
                "size": size,
                "total_pages": (total + size - 1) // size,
                "has_next": end_idx < total,
                "has_previous": page > 1
            },
            "statistics": data.get("statistics", {}),
            "metadata": {
                "date_range": f"{start_date.date()} to {end_date.date()}",
                "days": days,
                "filters_applied": {
                    "hazardous_only": hazardous_only,
                    "min_diameter_km": min_diameter_km,
                    "max_distance_km": max_distance_km,
                    "min_risk_score": min_risk_score,
                    "max_risk_score": max_risk_score
                },
                "processed_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching asteroid feed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch asteroid data: {str(e)}"
        )

@router.get("/{asteroid_id}", response_model=Dict[str, Any])
@asteroid_rate_limit
async def get_asteroid_details(
    asteroid_id: str,
    include_trajectory: bool = Query(True, description="Include 3D trajectory data"),
    include_orbital: bool = Query(True, description="Include orbital elements"),
    current_user: schemas.TokenData = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific asteroid"""
    try:
        # Try to get from database first
        db_asteroid = crud.AsteroidCRUD.get_asteroid(db, asteroid_id)
        
        if db_asteroid:
            # Convert database model to response
            response = {
                "id": db_asteroid.id,
                "name": db_asteroid.name,
                "designation": db_asteroid.designation,
                "absolute_magnitude_h": db_asteroid.absolute_magnitude_h,
                "estimated_diameter": {
                    "kilometers": {
                        "estimated_diameter_min": db_asteroid.estimated_diameter_min,
                        "estimated_diameter_max": db_asteroid.estimated_diameter_max
                    }
                },
                "is_potentially_hazardous": db_asteroid.is_potentially_hazardous,
                "close_approach_data": [{
                    "close_approach_date": db_asteroid.close_approach_date.isoformat() if db_asteroid.close_approach_date else None,
                    "miss_distance": {"kilometers": str(db_asteroid.miss_distance_km)},
                    "relative_velocity": {"kilometers_per_hour": str(db_asteroid.relative_velocity_kph)}
                }] if db_asteroid.close_approach_date else [],
                "orbital_data": db_asteroid.orbital_data,
                "risk_score": db_asteroid.risk_score,
                "threat_level": db_asteroid.threat_level,
                "is_sentry_object": db_asteroid.is_sentry_object,
                "last_observation_date": db_asteroid.last_observation_date,
                "orbit_determination_date": db_asteroid.orbit_determination_date,
                "source": "database",
                "cached_at": db_asteroid.updated_at or db_asteroid.created_at
            }
        else:
            # Fetch from NASA API
            fetcher = await get_nasa_fetcher()
            data = await fetcher.fetch_asteroid_details(asteroid_id)
            response = data
            response["source"] = "nasa_api"
            response["cached_at"] = datetime.now().isoformat()
        
        # Add additional data if requested
        if include_orbital and "orbital_data" in response:
            response["orbital_elements"] = fetcher._extract_orbital_elements(response)
        
        # Note: 3D trajectory would be calculated here if requested
        if include_trajectory:
            response["has_trajectory"] = True
            # In production, you would generate trajectory points here
        
        return response
        
    except Exception as e:
        logger.error(f"Error fetching asteroid details: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND 
            if "not found" in str(e).lower() 
            else status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch asteroid details: {str(e)}"
        )

@router.get("/batch/details", response_model=Dict[str, Any])
async def get_asteroids_batch(
    ids: str = Query(..., description="Comma-separated asteroid IDs"),
    current_user: schemas.TokenData = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get details for multiple asteroids"""
    try:
        asteroid_ids = [id.strip() for id in ids.split(",") if id.strip()]
        
        if len(asteroid_ids) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 50 asteroids per batch request"
            )
        
        fetcher = await get_nasa_fetcher()
        results = await fetcher.fetch_batch_details(asteroid_ids)
        
        return {
            "results": results,
            "statistics": {
                "requested": len(asteroid_ids),
                "found": len(results),
                "success_rate": (len(results) / len(asteroid_ids) * 100) if asteroid_ids else 0
            },
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "cache_utilization": "high"
            }
        }
        
    except Exception as e:
        logger.error(f"Error in batch details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch batch details: {str(e)}"
        )

@router.get("/statistics/summary", response_model=Dict[str, Any])
async def get_asteroid_statistics(
    period_days: int = Query(30, ge=1, le=365, description="Period in days"),
    current_user: schemas.TokenData = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get comprehensive asteroid statistics"""
    try:
        fetcher = await get_nasa_fetcher()
        statistics = await fetcher.get_statistics(period_days)
        
        return {
            **statistics,
            "metadata": {
                "period_days": period_days,
                "generated_at": datetime.now().isoformat(),
                "data_source": "NASA NeoWS API"
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch statistics: {str(e)}"
        )

@router.get("/close-approaches/upcoming", response_model=Dict[str, Any])
async def get_upcoming_close_approaches(
    days: int = Query(30, ge=1, le=180, description="Look ahead days"),
    max_distance_ld: float = Query(10, ge=0.1, description="Maximum distance in Lunar Distances"),
    hazardous_only: bool = Query(False, description="Filter only hazardous asteroids"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: schemas.TokenData = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get upcoming close approaches"""
    try:
        max_distance_km = max_distance_ld * 384400  # Convert LD to km
        
        # Fetch data
        fetcher = await get_nasa_fetcher()
        end_date = datetime.now() + timedelta(days=days)
        data = await fetcher.fetch_feed(
            datetime.now().strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
        
        # Process close approaches
        close_approaches = []
        for asteroid in data.get("asteroids", []):
            if not asteroid.get("close_approach_data"):
                continue
            
            for approach in asteroid["close_approach_data"]:
                try:
                    distance_km = float(approach["miss_distance"]["kilometers"])
                    distance_ld = distance_km / 384400
                    
                    if distance_ld > max_distance_ld:
                        continue
                    
                    if hazardous_only and not asteroid["is_potentially_hazardous"]:
                        continue
                    
                    close_approaches.append({
                        "asteroid": asteroid,
                        "approach": approach,
                        "distance_km": distance_km,
                        "distance_ld": round(distance_ld, 3)
                    })
                except (KeyError, ValueError):
                    continue
        
        # Sort by distance
        close_approaches.sort(key=lambda x: x["distance_km"])
        
        # Pagination
        total = len(close_approaches)
        start_idx = (page - 1) * size
        end_idx = start_idx + size
        paginated = close_approaches[start_idx:end_idx]
        
        return {
            "close_approaches": paginated,
            "pagination": {
                "total": total,
                "page": page,
                "size": size,
                "total_pages": (total + size - 1) // size,
                "has_next": end_idx < total,
                "has_previous": page > 1
            },
            "parameters": {
                "days": days,
                "max_distance_ld": max_distance_ld,
                "hazardous_only": hazardous_only
            },
            "statistics": {
                "total_approaches": total,
                "closest_approach": close_approaches[0] if close_approaches else None,
                "average_distance_ld": sum(ca["distance_ld"] for ca in close_approaches) / total if total > 0 else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching close approaches: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch close approaches: {str(e)}"
        )

@router.get("/search", response_model=Dict[str, Any])
@search_rate_limit
async def search_asteroids(
    query: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    current_user: schemas.TokenData = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Search asteroids by name or designation"""
    try:
        # Fetch recent data for search
        fetcher = await get_nasa_fetcher()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        data = await fetcher.fetch_feed(
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
        
        # Search logic
        results = []
        query_lower = query.lower()
        
        for asteroid in data.get("asteroids", []):
            asteroid_name = asteroid.get("name", "").lower()
            asteroid_id = asteroid.get("id", "").lower()
            designation = asteroid.get("designation", "").lower()
            
            if (query_lower in asteroid_name or 
                query_lower in asteroid_id or
                query_lower in designation):
                
                results.append(asteroid)
                
                if len(results) >= limit:
                    break
        
        return {
            "query": query,
            "results": results,
            "total_found": len(results),
            "search_scope": "30 days of asteroid data",
            "metadata": {
                "searched_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )

@router.get("/hazardous/top", response_model=Dict[str, Any])
async def get_top_hazardous_asteroids(
    limit: int = Query(10, ge=1, le=50, description="Number of asteroids to return"),
    days: int = Query(7, ge=1, le=30, description="Days to look back"),
    current_user: schemas.TokenData = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get top hazardous asteroids by risk score"""
    try:
        # Fetch data
        fetcher = await get_nasa_fetcher()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        data = await fetcher.fetch_feed(
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
        
        # Filter and sort hazardous asteroids
        hazardous = [a for a in data.get("asteroids", []) 
                    if a.get("is_potentially_hazardous", False)]
        
        hazardous.sort(key=lambda x: x.get("risk_score", 0), reverse=True)
        top_hazardous = hazardous[:limit]
        
        return {
            "asteroids": top_hazardous,
            "total_hazardous": len(hazardous),
            "period_days": days,
            "risk_thresholds": {
                "critical": sum(1 for a in top_hazardous if a.get("threat_level") == "Critical"),
                "high": sum(1 for a in top_hazardous if a.get("threat_level") == "High"),
                "moderate": sum(1 for a in top_hazardous if a.get("threat_level") == "Moderate")
            },
            "metadata": {
                "generated_at": datetime.now().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error fetching top hazardous: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch top hazardous asteroids: {str(e)}"
        )