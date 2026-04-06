from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Dict, Any
from auth.cognito import get_current_user
from services.clustering_service import compute_clusters
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/clusters")
async def get_clusters(
    mode: str = Query("combined"),
    time_eps_minutes: int = Query(60),
    distance_eps_km: float = Query(1.0),
    min_samples: int = Query(2),
    user_id: str = Depends(get_current_user)
) -> Dict[str, Any]:

    if mode not in ["time", "location", "combined"]:
        raise HTTPException(status_code=400, detail="Invalid mode")

    try:
        logger.info(f"Computing clusters for user {user_id}, mode={mode}")
        return compute_clusters(user_id, mode, time_eps_minutes, distance_eps_km, min_samples)

    except Exception as e:
        logger.error(f"Failed to fetch clusters: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch clusters: {str(e)}")