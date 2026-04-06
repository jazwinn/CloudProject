import piexif
from PIL import Image
from typing import Dict, Any, Optional
import io
from datetime import datetime

from pillow_heif import register_heif_opener
register_heif_opener()

def _convert_to_degrees(value) -> float:
    """Helper function to convert EXIF GPS rationals to decimal degrees float."""
    try:
        d, m, s = value
        d_deg = d[0] / d[1] if d[1] != 0 else 0
        m_deg = m[0] / m[1] if m[1] != 0 else 0
        s_deg = s[0] / s[1] if s[1] != 0 else 0
        return d_deg + (m_deg / 60.0) + (s_deg / 3600.0)
    except Exception:
        return 0.0

def _parse_exif_datetime(date_string: str) -> Optional[str]:
    """Converts EXIF date format 'YYYY:MM:DD HH:MM:SS' into ISO 8601 'YYYY-MM-DDTHH:MM:SS'."""
    try:
        dt = datetime.strptime(date_string, "%Y:%m:%d %H:%M:%S")
        return dt.isoformat()
    except ValueError:
        return None

def extract_exif_metadata(file_bytes: bytes) -> Dict[str, Optional[Any]]:
    """
    Extracts EXIF metadata from raw image bytes.
    Always returns a predefined standard layout dictionary:
    {
        "date_taken": str | None (ISO 8601),
        "gps_lat": float | None,
        "gps_lon": float | None
    }
    """
    metadata = {
        "date_taken": None,
        "gps_lat": None,
        "gps_lon": None
    }
    
    try:
        img = Image.open(io.BytesIO(file_bytes))
        
        if "exif" not in img.info:
            return metadata
            
        exif_dict = piexif.load(img.info["exif"])
        
        # Parse Date Taken
        if piexif.ExifIFD.DateTimeOriginal in exif_dict.get("Exif", {}):
            date_bytes = exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal]
            date_str = date_bytes.decode('utf-8')
            metadata["date_taken"] = _parse_exif_datetime(date_str)
            
        # Parse GPS
        gps_ifd = exif_dict.get("GPS", {})
        if gps_ifd:
            lat = gps_ifd.get(piexif.GPSIFD.GPSLatitude)
            lat_ref = gps_ifd.get(piexif.GPSIFD.GPSLatitudeRef)
            lon = gps_ifd.get(piexif.GPSIFD.GPSLongitude)
            lon_ref = gps_ifd.get(piexif.GPSIFD.GPSLongitudeRef)
            
            if lat and lat_ref and lon and lon_ref:
                lat_ref_str = lat_ref.decode('utf-8') if isinstance(lat_ref, bytes) else lat_ref
                lon_ref_str = lon_ref.decode('utf-8') if isinstance(lon_ref, bytes) else lon_ref
                
                lat_val = _convert_to_degrees(lat)
                lon_val = _convert_to_degrees(lon)
                
                if lat_ref_str != "N":
                    lat_val = -lat_val
                if lon_ref_str != "E":
                    lon_val = -lon_val
                    
                metadata["gps_lat"] = round(lat_val, 6)
                metadata["gps_lon"] = round(lon_val, 6)

    except Exception as e:
        print(f"Failed to extract EXIF data: {e}")
        # Failure merely guarantees the dict structure returns Nones
        pass
        
    return metadata
