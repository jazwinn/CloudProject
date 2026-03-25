from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Dict, Any
from auth.cognito import get_current_user
from services.graph_service import build_graph
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/graph")
def get_relationship_graph(
    time_threshold_minutes: int = Query(60, description="Time boundary clustering offset in minutes."),
    distance_threshold_km: float = Query(1.0, description="Spatial Haversine boundary clustering in kilometers."),
    user_id: str = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Exposes a dynamic contextual connection mapping graph structured properly for frontend D3 integration.
    """
    try:
        graph = build_graph(
            user_id=user_id,
            time_threshold_minutes=time_threshold_minutes,
            dist_threshold_km=distance_threshold_km
        )
        return graph
    except Exception as e:
        logger.error(f"REST Graph mapping layer crashed fetching elements implicitly: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch and process mapping graph")
