# Deploy with reserved concurrency = 10 to prevent runaway DBSCAN jobs.
# Set via: aws lambda put-function-concurrency --function-name clustering_processor --reserved-concurrent-executions 10
import os
import json
import logging
import sys
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.clustering_service import compute_clusters
from services.database import get_db, ClusterResult

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Asynchronously computes photo clusters based on time and location metadata.
    Results are cached in the PostgreSQL `cluster_results` table.
    """
    try:
        user_id = event.get("user_id")
        mode = event.get("mode", "combined")
        time_eps_minutes = event.get("time_eps_minutes", 60)
        distance_eps_km = event.get("distance_eps_km", 1.0)
        min_samples = event.get("min_samples", 2)
        
        if not user_id:
            logger.error("Missing user_id in clustering event.")
            return {"status": "error", "message": "Missing user_id"}
            
        logger.info(f"Starting clustering for user: {user_id}")
        
        result = compute_clusters(
            user_id=user_id,
            mode=mode,
            time_eps_minutes=time_eps_minutes,
            distance_eps_km=distance_eps_km,
            min_samples=min_samples
        )
        
        with get_db() as session:
            record = ClusterResult(
                user_id=user_id,
                computed_at=datetime.now(timezone.utc).isoformat(),
                mode=mode,
                result=json.dumps(result)
            )
            session.add(record)
        
        logger.info(f"Successfully computed and cached clusters for user: {user_id}")
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Clustering processor failed: {e}")
        raise e
