import boto3
from boto3.dynamodb.conditions import Attr
from config import get_settings
from utils.geo import haversine
from datetime import datetime
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

def get_dynamodb_resource():
    settings = get_settings()
    return boto3.resource(
        'dynamodb',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        aws_session_token=settings.AWS_SESSION_TOKEN,
        region_name=settings.AWS_REGION
    )

def _parse_iso(date_str: str) -> datetime | None:
    try:
        return datetime.fromisoformat(date_str)
    except Exception:
        return None

def build_graph(
    user_id: str, 
    time_threshold_minutes: int = 60, 
    dist_threshold_km: float = 1.0
) -> Dict[str, List[Any]]:
    """
    Fetches user photos from DynamoDB and computes relationships.
    
    PERFORMANCE NOTE: Photo comparisons loop at O(n^2). For large scale systems 
    this compute-intensive logic should be offloaded onto standard ETL pipelines 
    mapped efficiently to a spatial graph database indexing map, handled securely 
    by an AWS Lambda backend rather than synchronous API logic.
    """
    settings = get_settings()
    
    try:
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(settings.DYNAMO_TABLE_NAME)
        
        # In a fully migrated AWS model, an active GSI index against user_id natively 
        # utilizes `table.query()` securely returning lists. Assuming base level model:
        response = table.scan(
            FilterExpression=Attr('user_id').eq(user_id)
        )
        items = response.get('Items', [])
        
        # Paginated handling
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                FilterExpression=Attr('user_id').eq(user_id),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response.get('Items', []))
            
    except Exception as e:
        logger.error(f"Failed to scan DynamoDB for graph relationships: {e}")
        return {"nodes": [], "edges": []}

    nodes = []
    
    # Structuring standard Node mapping blocks
    for item in items:
        # Guarantee baseline Dict fields implicitly requested natively
        node = {
            "id": item.get('image_id'),
            "date_taken": item.get('date_taken'),
        }
        
        if "gps_lat" in item and item["gps_lat"] is not None:
            node["gps_lat"] = float(item["gps_lat"])
        else:
            node["gps_lat"] = None
            
        if "gps_lon" in item and item["gps_lon"] is not None:
            node["gps_lon"] = float(item["gps_lon"])
        else:
            node["gps_lon"] = None
            
        nodes.append(node)

    edges = []
    
    # Edge threshold escapes efficiently if caller possesses 0 or 1 Node points
    if len(nodes) < 2:
        return {"nodes": nodes, "edges": []}

    time_delta_seconds = time_threshold_minutes * 60
    
    # O(n^2) internal comparison looping dynamically calculating valid paths
    for i in range(len(nodes)):
        node_a = nodes[i]
        date_a = _parse_iso(node_a["date_taken"]) if node_a.get("date_taken") else None
        lat_a, lon_a = node_a.get("gps_lat"), node_a.get("gps_lon")
        
        for j in range(i + 1, len(nodes)):
            node_b = nodes[j]
            relationships = []
            
            # --- Time Boundary Edge Test ---
            date_b = _parse_iso(node_b["date_taken"]) if node_b.get("date_taken") else None
            if date_a and date_b:
                diff_seconds = abs((date_a - date_b).total_seconds())
                if diff_seconds <= time_delta_seconds:
                    relationships.append("time")
            
            # --- Location Geo Boundary Edge Test ---
            lat_b, lon_b = node_b.get("gps_lat"), node_b.get("gps_lon")
            if lat_a is not None and lon_a is not None and lat_b is not None and lon_b is not None:
                dist_km = haversine(lat_a, lon_a, lat_b, lon_b)
                if dist_km <= dist_threshold_km:
                    relationships.append("location")
            
            # Save final relational vectors dynamically
            if relationships:
                edges.append({
                    "source": node_a["id"],
                    "target": node_b["id"],
                    "relationship": "+".join(relationships)
                })

    return {"nodes": nodes, "edges": edges}
