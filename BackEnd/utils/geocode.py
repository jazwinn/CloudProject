import requests
import logging
import time

logger = logging.getLogger(__name__)

# In-memory cache with TTL
_geocode_cache = {}
CACHE_TTL = 86400  # 1 day
MAX_CACHE_SIZE = 10000

# Rate limiting (Nominatim allows ~1 req/sec)
_last_call_time = 0

# Temporary block if we get rate limited
_nominatim_blocked_until = 0


def _rate_limit():
    global _last_call_time
    now = time.time()
    elapsed = now - _last_call_time
    if elapsed < 1.1:
        time.sleep(1.1 - elapsed)
    _last_call_time = time.time()


def _get_cached(key):
    entry = _geocode_cache.get(key)
    if not entry:
        return None

    value, ts = entry
    if time.time() - ts > CACHE_TTL:
        del _geocode_cache[key]
        return None

    return value


def _set_cache(key, value):
    if len(_geocode_cache) > MAX_CACHE_SIZE:
        logger.warning("Geocode cache cleared (max size reached)")
        _geocode_cache.clear()

    _geocode_cache[key] = (value, time.time())


def _is_blocked():
    return time.time() < _nominatim_blocked_until


def _block_temporarily():
    global _nominatim_blocked_until
    _nominatim_blocked_until = time.time() + 60  # block for 1 minute
    logger.warning("Nominatim temporarily blocked due to rate limiting (429)")


def get_city_name(lat: float, lon: float) -> str:
    """
    Reverse geocodes a lat/lon to a city/region name using Nominatim.
    Includes caching, rate limiting, and failure protection.
    """

    if lat is None or lon is None:
        return "Unknown Location"

    # Block if we're being rate limited
    if _is_blocked():
        return "Unknown Location"

    # Round to ~1km grid for cache efficiency
    cache_key = f"{round(lat, 2):.2f},{round(lon, 2):.2f}"

    cached = _get_cached(cache_key)
    if cached:
        return cached

    url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": lat,
        "lon": lon,
        "format": "jsonv2",
        "zoom": 10
    }

    headers = {
        "User-Agent": "CloudGraph-PhotoApp-v2"
    }

    try:
        _rate_limit()

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=3
        )
        response.raise_for_status()

        data = response.json()
        address = data.get("address", {})

        city = (
            address.get("city") or
            address.get("town") or
            address.get("village") or
            address.get("suburb") or
            address.get("county") or
            address.get("state") or
            address.get("country")
        )

        label = str(city) if city else "Unknown Location"
        _set_cache(cache_key, label)
        return label

    except Exception as e:
        # Detect rate limiting
        if "429" in str(e):
            _block_temporarily()

        logger.error(f"Nominatim failure for {lat},{lon}: {e}")
        return "Unknown Location"