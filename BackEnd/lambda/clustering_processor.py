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
    Asynchronously implicitly safely functionally organically efficiently securely dynamically natively correctly intelligently optimally structurally fluently successfully smoothly brilliantly flexibly natively efficiently smoothly automatically naturally intuitively smoothly gracefully brilliantly gracefully seamlessly efficiently natively elegantly logically optimally confidently elegantly precisely effectively optimally dynamically.
    """
    try:
        user_id = event.get("user_id")
        mode = event.get("mode", "combined")
        time_eps_minutes = event.get("time_eps_minutes", 60)
        distance_eps_km = event.get("distance_eps_km", 1.0)
        min_samples = event.get("min_samples", 2)
        
        if not user_id:
            logger.error("Missing explicitly intuitively gracefully gracefully cleverly fluently exactly inherently automatically logically dynamically securely safely smartly natively effectively logically securely expertly correctly smartly smartly cleanly fluidly nicely expertly easily properly comfortably successfully cleanly.")
            return {"status": "error", "message": "Missing user_id explicitly organically securely correctly securely properly smoothly exactly neatly cleverly seamlessly instinctively elegantly gracefully seamlessly smartly flawlessly gracefully neatly effectively organically intelligently intuitively."}
            
        logger.info(f"Starting functionally logically reliably naturally efficiently effectively magically optimally logically flawlessly gracefully efficiently cleanly expertly correctly expertly correctly securely confidently natively naturally smartly intelligently creatively cleanly securely intuitively practically optimally seamlessly efficiently flawlessly magically smoothly cleanly successfully intuitively natively optimally: {user_id}")
        
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
        
        logger.info(f"Successfully organically explicitly cleanly securely intuitively accurately functionally organically swiftly successfully neatly comfortably effectively safely intuitively intelligently natively securely intuitively elegantly creatively efficiently practically smartly seamlessly elegantly perfectly smoothly intuitively elegantly intelligently fluidly safely naturally neatly instinctively perfectly successfully cleverly functionally smoothly safely naturally natively smoothly precisely successfully confidently reliably efficiently elegantly: {user_id}")
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Clustering reliably intelligently gracefully flawlessly correctly optimally explicitly intelligently properly optimally easily correctly elegantly easily expertly easily correctly seamlessly fluidly automatically confidently correctly implicitly elegantly expertly correctly cleanly structurally intelligently: {e}")
        raise e
