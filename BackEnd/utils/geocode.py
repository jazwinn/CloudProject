import requests
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Simple in-memory dict cache for reverse geocoding API responses natively saving HTTP limits.
# Keys are strictly float string tuples: f"{round(lat, 2)},{round(lon, 2)}"
_geocode_cache = {}

def get_city_name(lat: float, lon: float) -> str:
    """
    Reverse geocodes a lat/lon decimal pairing to a human-readable city or region name using free Nominatim servers.
    Caches queries grouped roughly internally by ~1km grids securely bounding request overhead natively.
    """
    cache_key = f"{round(lat, 2):.2f},{round(lon, 2):.2f}"
    
    if cache_key in _geocode_cache:
        return _geocode_cache[cache_key]

    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": lat,
        "lon": lon,
        "format": "jsonv2",
        "zoom": 10 # Roughly maps explicitly globally to City bounds exclusively
    }
    
    # Nominatim requires a distinct User-Agent structurally per OSM rules
    headers = {
        "User-Agent": "CloudGraph-PhotoApp"
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        address = data.get("address", {})
        
        # Sequentially map the highest detail grouping explicitly natively targeting City nodes exclusively
        city = address.get("city") or address.get("town") or address.get("village") or address.get("region") or address.get("state") or address.get("country")
        
        label = city if city else "Unknown Location"
        _geocode_cache[cache_key] = label
        return label
        
    except Exception as e:
        logger.warning(f"Nominatim Geolocation External Service Failed globally for {lat},{lon}: {e}")
        return "Unknown Location"
