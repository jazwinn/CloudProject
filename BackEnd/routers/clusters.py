from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Dict, Any
from auth.cognito import get_current_user
from services.clustering_service import compute_clusters
from services.lambda_service import invoke_clustering_lambda
from services.database import get_db, ImageMetadata, ClusterResult
from datetime import datetime, timezone, timedelta
import json
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
        with get_db() as session:
            # 1. Count photos for this user
            items_count = (
                session.query(ImageMetadata)
                .filter(ImageMetadata.user_id == user_id)
                .count()
            )

            # 2. Check sync vs async threshold
            if items_count < 0:
                return compute_clusters(user_id, mode, time_eps_minutes, distance_eps_km, min_samples)

            # 3. Check for a fresh cached ClusterResult
            try:
                latest = (
                    session.query(ClusterResult)
                    .filter(ClusterResult.user_id == user_id, ClusterResult.mode == mode)
                    .order_by(ClusterResult.computed_at.desc())
                    .first()
                )

                if latest:
                    computed_time = datetime.fromisoformat(latest.computed_at)
                    if datetime.now(timezone.utc) - computed_time < timedelta(minutes=10):
                        logger.info("Returning fresh cached cluster result from database")
                        return json.loads(latest.result)

            except Exception as e:
                logger.warning(f"Failed to query ClusterResults: {e}")
                # Fallthrough to Lambda

        # 4. Invoke Lambda async (outside DB session — Lambda is async, no DB needed here)
        invoke_clustering_lambda(user_id, mode, time_eps_minutes, distance_eps_km, min_samples)

        return {
            "status": "processing",
            "message": "Clustering started, check back in a few seconds"
        }

    except Exception as e:
        logger.error(f"Failed to fetch clusters: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch clusters: {str(e)}")
