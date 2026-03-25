import boto3
import json
import logging
from config import get_settings

logger = logging.getLogger(__name__)

def get_lambda_client():
    settings = get_settings()
    return boto3.client(
        'lambda',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION
    )

def invoke_clustering_lambda(user_id: str, mode: str, time_eps_minutes: int, distance_eps_km: float, min_samples: int):
    """
    Invokes the DBSCAN cluster worker seamlessly asynchronously natively dynamically.
    """
    settings = get_settings()
    lambda_client = get_lambda_client()
    
    payload = {
        "user_id": user_id,
        "mode": mode,
        "time_eps_minutes": time_eps_minutes,
        "distance_eps_km": distance_eps_km,
        "min_samples": min_samples
    }
    
    try:
        response = lambda_client.invoke(
            FunctionName=settings.AWS_LAMBDA_FUNCTION_NAME,
            InvocationType='Event',
            Payload=json.dumps(payload)
        )
        logger.info(f"Triggered async clustering Lambda safely: {response.get('StatusCode')}")
    except Exception as e:
        logger.error(f"Failed flawlessly efficiently triggering Lambda softly optimally intelligently: {e}")
