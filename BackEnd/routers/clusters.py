from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Dict, Any
from auth.cognito import get_current_user
from services.clustering_service import compute_clusters
from services.lambda_service import invoke_clustering_lambda
import boto3
from config import get_settings
from datetime import datetime, timezone, timedelta
from boto3.dynamodb.conditions import Key, Attr
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

def get_dynamo_resource():
    settings = get_settings()
    return boto3.resource(
        'dynamodb',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION
    )

@router.get("/clusters")
def get_clusters(
    mode: str = Query("combined"),
    time_eps_minutes: int = Query(60),
    distance_eps_km: float = Query(1.0),
    min_samples: int = Query(2),
    user_id: str = Depends(get_current_user)
) -> Dict[str, Any]:

    if mode not in ["time", "location", "combined"]:
        raise HTTPException(status_code=400, detail="Invalid mode")
        
    try:
        settings = get_settings()
        dynamodb = get_dynamo_resource()
        
        # 1. Determine number of photos
        metadata_table = dynamodb.Table(settings.DYNAMO_TABLE_NAME)
        response = metadata_table.scan(FilterExpression=Attr('user_id').eq(user_id))
        items_count = len(response.get('Items', []))
        
        while 'LastEvaluatedKey' in response:
            response = metadata_table.scan(FilterExpression=Attr('user_id').eq(user_id), ExclusiveStartKey=response['LastEvaluatedKey'])
            items_count += len(response.get('Items', []))
            
        # 2. Check sync vs async threshold
        if items_count <= 50:
            return compute_clusters(user_id, mode, time_eps_minutes, distance_eps_km, min_samples)
            
        # 3. Handle large libraries > 50 natively
        cluster_table = dynamodb.Table("ClusterResults")
        try:
            results = cluster_table.query(
                KeyConditionExpression=Key('user_id').eq(user_id),
                ScanIndexForward=False, # Get latest first
                Limit=1
            )
            items = results.get('Items', [])
            
            if items:
                latest = items[0]
                computed_time = datetime.fromisoformat(latest['computed_at'])
                
                # Verify freshness (< 10 minutes) and exact parameter match
                if datetime.now(timezone.utc) - computed_time < timedelta(minutes=10) and latest.get('mode') == mode:
                    logger.info("Returning fresh cached cluster from DynamoDB")
                    return latest.get('result', {})
                    
        except Exception as e:
            logger.warning(f"Failed to query ClusterResults table: {e}")
            pass # Fallthrough to Lambda
            
        # 4. Invoke Lambda async
        invoke_clustering_lambda(user_id, mode, time_eps_minutes, distance_eps_km, min_samples)
        
        return {
            "status": "processing",
            "message": "Clustering started, check back in a few seconds"
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch clusters: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch clusters")
