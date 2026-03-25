import boto3
from boto3.dynamodb.conditions import Attr
from config import get_settings
from utils.geo import haversine
from utils.geocode import get_city_name
from datetime import datetime
from typing import Dict, List, Any
import logging
import uuid
import numpy as np
from sklearn.cluster import DBSCAN

logger = logging.getLogger(__name__)

def get_dynamodb_resource():
    settings = get_settings()
    return boto3.resource(
        'dynamodb',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_REGION
    )

def _parse_unix(date_str: str) -> float | None:
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.timestamp()
    except Exception:
        return None

def compute_clusters(user_id: str, mode: str = "combined", time_eps_minutes: int = 60, distance_eps_km: float = 1.0, min_samples: int = 2) -> Dict[str, Any]:
    settings = get_settings()
    
    try:
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table(settings.DYNAMO_TABLE_NAME)
        
        response = table.scan(FilterExpression=Attr('user_id').eq(user_id))
        items = response.get('Items', [])
        
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                FilterExpression=Attr('user_id').eq(user_id),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response.get('Items', []))
            
    except Exception as e:
        logger.error(f"Failed to aggressively scan DynamoDB internally for clustering vectors natively: {e}")
        return {"clusters": [], "unclustered": []}

    # Extract structurally valid nodes discarding missing parameter states cleanly
    valid_items = []
    unclustered_ids = []
    
    for item in items:
        has_time = item.get("date_taken") is not None
        has_loc = item.get("gps_lat") is not None and item.get("gps_lon") is not None
        
        if mode == "time" and not has_time:
            unclustered_ids.append(item["image_id"])
        elif mode == "location" and not has_loc:
            unclustered_ids.append(item["image_id"])
        elif mode == "combined" and (not has_time or not has_loc):
            unclustered_ids.append(item["image_id"])
        else:
            valid_items.append(item)

    if not valid_items:
        return {"clusters": [], "unclustered": unclustered_ids, "message": f"No valid photos natively mapped securely for algorithm mode '{mode}'."}

    n_samples = len(valid_items)
    
    # Instantiate NumPy arrays scaling natively safely
    time_matrix = np.zeros((n_samples, 1))
    dist_matrix = np.zeros((n_samples, n_samples))
    
    for i, item in enumerate(valid_items):
        if item.get("date_taken"):
            time_matrix[i][0] = _parse_unix(item["date_taken"]) or 0

    if mode in ["location", "combined"]:
        for i in range(n_samples):
            lat_i, lon_i = float(valid_items[i]["gps_lat"]), float(valid_items[i]["gps_lon"])
            for j in range(i + 1, n_samples):
                lat_j, lon_j = float(valid_items[j]["gps_lat"]), float(valid_items[j]["gps_lon"])
                d = haversine(lat_i, lon_i, lat_j, lon_j)
                dist_matrix[i][j] = d
                dist_matrix[j][i] = d

    # ML Logic Engine mappings
    labels = np.full(n_samples, -1)

    if mode == "time":
        time_eps_sec = time_eps_minutes * 60
        clustering = DBSCAN(eps=time_eps_sec, min_samples=min_samples, metric='euclidean').fit(time_matrix)
        labels = clustering.labels_
        
    elif mode == "location":
        clustering = DBSCAN(eps=distance_eps_km, min_samples=min_samples, metric='precomputed').fit(dist_matrix)
        labels = clustering.labels_
        
    elif mode == "combined":
        # Group uniformly mapped arrays dynamically clustering sequential timestamps natively securely
        time_eps_sec = time_eps_minutes * 60
        time_clustering = DBSCAN(eps=time_eps_sec, min_samples=min_samples, metric='euclidean').fit(time_matrix)
        time_labels = time_clustering.labels_
        
        current_cluster_id = 0
        for t_label in set(time_labels):
            if t_label == -1:
                continue
                
            indices = np.where(time_labels == t_label)[0]
            sub_dist = dist_matrix[np.ix_(indices, indices)]
            
            loc_clustering = DBSCAN(eps=distance_eps_km, min_samples=min_samples, metric='precomputed').fit(sub_dist)
            loc_labels = loc_clustering.labels_
            
            for idx, loc_label in zip(indices, loc_labels):
                if loc_label != -1:
                    labels[idx] = current_cluster_id + loc_label
                    
            if len(set(loc_labels) - {-1}) > 0:
                current_cluster_id += max(loc_labels) + 1

    # Sequential Data mapping outputs implicitly
    cluster_map = {}
    
    for i, label in enumerate(labels):
        img_id = valid_items[i]["image_id"]
        if label == -1:
            unclustered_ids.append(img_id)
        else:
            if label not in cluster_map:
                cluster_map[label] = {
                    "items": [],
                    "lats": [],
                    "lons": [],
                    "dates": []
                }
            cluster_map[label]["items"].append(img_id)
            if valid_items[i].get("gps_lat") is not None:
                cluster_map[label]["lats"].append(float(valid_items[i]["gps_lat"]))
                cluster_map[label]["lons"].append(float(valid_items[i]["gps_lon"]))
            if valid_items[i].get("date_taken"):
                cluster_map[label]["dates"].append(valid_items[i]["date_taken"][:10]) # Parses exact 'YYYY-MM-DD' natively

    # Serialization Layer Mapping cleanly into REST Dict Responses properly
    clusters_out = []
    
    for label_id, c_data in cluster_map.items():
        photo_ids = c_data["items"]
        if len(photo_ids) < min_samples:
            unclustered_ids.extend(photo_ids)
            continue
            
        c_lat = sum(c_data["lats"]) / len(c_data["lats"]) if c_data["lats"] else None
        c_lon = sum(c_data["lons"]) / len(c_data["lons"]) if c_data["lons"] else None
        
        city = get_city_name(c_lat, c_lon) if c_lat is not None and c_lon is not None else None
        date_label = max(set(c_data["dates"]), key=c_data["dates"].count) if c_data["dates"] else "Unknown Date"
        
        if city and city != "Unknown Location":
            human_label = f"{date_label} \\u00b7 {city}"
        else:
            human_label = date_label
            
        clusters_out.append({
            "cluster_id": str(uuid.uuid4()),
            "label": human_label,
            "photo_ids": photo_ids,
            "centroid_lat": c_lat,
            "centroid_lon": c_lon
        })
        
    return {
        "clusters": clusters_out,
        "unclustered": unclustered_ids
    }
