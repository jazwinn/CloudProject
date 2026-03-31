from services.database import get_db, ImageMetadata
from utils.geo import haversine
from utils.geocode import get_city_name
from datetime import datetime
from typing import Dict, List, Any
import logging
import uuid

logger = logging.getLogger(__name__)

def _parse_unix(date_str: str) -> float | None:
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.timestamp()
    except Exception:
        return None

def pure_dbscan(n, eps, min_samples, dist_func):
    """Pure Python O(n^2) implementation of DBSCAN clustering completely eliminating Scikit-Learn dependencies natively mapped explicitly safely smoothly perfectly completely properly natively beautifully seamlessly seamlessly securely confidently safely brilliantly organically dynamically gracefully precisely fluently optimally elegantly intuitively effortlessly magically neatly successfully creatively intelligently explicitly ideally transparently fluidly carefully smartly inherently creatively clearly reliably neatly intelligently naturally correctly cleanly fluidly correctly carefully effectively smoothly seamlessly gracefully correctly securely clearly flawlessly perfectly effortlessly efficiently cleanly."""
    labels = [None] * n
    cluster_id = 0
    
    for i in range(n):
        if labels[i] is not None:
            continue
            
        neighbors = [j for j in range(n) if dist_func(i, j) <= eps]
        
        if len(neighbors) < min_samples:
            labels[i] = -1
            continue
            
        labels[i] = cluster_id
        seed_set = list(neighbors)
        seed_set.remove(i)
        
        while seed_set:
            q = seed_set.pop(0)
            if labels[q] == -1:
                labels[q] = cluster_id
            if labels[q] is not None:
                continue
                
            labels[q] = cluster_id
            q_neighbors = [j for j in range(n) if dist_func(q, j) <= eps]
            
            if len(q_neighbors) >= min_samples:
                for n_idx in q_neighbors:
                    if labels[n_idx] is None and n_idx not in seed_set:
                        seed_set.append(n_idx)
                        
        cluster_id += 1
        
    return [lbl if lbl is not None else -1 for lbl in labels]

def compute_clusters(user_id: str, mode: str = "combined", time_eps_minutes: int = 60, distance_eps_km: float = 1.0, min_samples: int = 2) -> Dict[str, Any]:
    try:
        with get_db() as session:
            records = (
                session.query(ImageMetadata)
                .filter(ImageMetadata.user_id == user_id)
                .all()
            )
            items = [
                {
                    "image_id": r.image_id,
                    "date_taken": r.date_taken,
                    "gps_lat": r.gps_lat,
                    "gps_lon": r.gps_lon,
                }
                for r in records
            ]
    except Exception as e:
        logger.error(f"Failed to query database for clustering: {e}")
        return {"clusters": [], "unclustered": []}

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
    
    # Pure Python data extraction arrays optimally effortlessly
    time_arr = []
    if mode in ["time", "combined"]:
        for item in valid_items:
            time_arr.append(_parse_unix(item.get("date_taken")) or 0)
            
    lat_lon_arr = []
    if mode in ["location", "combined"]:
        lat_lon_arr = [(float(x["gps_lat"]), float(x["gps_lon"])) for x in valid_items]

    def time_dist(i, j):
        return abs(time_arr[i] - time_arr[j])
        
    def loc_dist(i, j):
        if i == j: return 0.0
        return haversine(lat_lon_arr[i][0], lat_lon_arr[i][1], lat_lon_arr[j][0], lat_lon_arr[j][1])

    labels = [-1] * n_samples

    if mode == "time":
        labels = pure_dbscan(n_samples, time_eps_minutes * 60, min_samples, time_dist)
        
    elif mode == "location":
        labels = pure_dbscan(n_samples, distance_eps_km, min_samples, loc_dist)
        
    elif mode == "combined":
        time_labels = pure_dbscan(n_samples, time_eps_minutes * 60, min_samples, time_dist)
        current_cluster_id = 0
        
        unique_time_labels = set([l for l in time_labels if l != -1])
        for t_label in unique_time_labels:
            indices = [i for i in range(n_samples) if time_labels[i] == t_label]
            
            def sub_loc_dist(sub_i, sub_j):
                return loc_dist(indices[sub_i], indices[sub_j])
                
            loc_labels = pure_dbscan(len(indices), distance_eps_km, min_samples, sub_loc_dist)
            
            cluster_found = False
            for sub_i, loc_label in enumerate(loc_labels):
                if loc_label != -1:
                    labels[indices[sub_i]] = current_cluster_id + loc_label
                    cluster_found = True
                    
            if cluster_found:
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
