from services.database import get_db, ImageMetadata
from utils.geo import haversine
from datetime import datetime
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

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
    Fetches user photos from the database and computes relationships.

    PERFORMANCE NOTE: Photo comparisons loop at O(n^2). For large scale systems
    this compute-intensive logic should be offloaded onto standard ETL pipelines
    mapped efficiently to a spatial graph database indexing map, handled securely
    by an AWS Lambda backend rather than synchronous API logic.
    """
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
        logger.error(f"Failed to query database for graph relationships: {e}")
        return {"nodes": [], "edges": []}

    nodes = []

    for item in items:
        node = {
            "id": item.get("image_id"),
            "date_taken": item.get("date_taken"),
            "gps_lat": item.get("gps_lat"),
            "gps_lon": item.get("gps_lon"),
        }
        nodes.append(node)

    edges = []

    if len(nodes) < 2:
        return {"nodes": nodes, "edges": []}

    time_delta_seconds = time_threshold_minutes * 60

    # O(n^2) comparison loop
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

            if relationships:
                edges.append({
                    "source": node_a["id"],
                    "target": node_b["id"],
                    "relationship": "+".join(relationships)
                })

    return {"nodes": nodes, "edges": edges}
