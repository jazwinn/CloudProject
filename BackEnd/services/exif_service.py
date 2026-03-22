import piexif
from PIL import Image
from typing import Dict, Any
import io

def _convert_to_degrees(value) -> float:
    """Helper function to convert EXIF GPS rationals to decimal degrees float."""
    d, m, s = value
    # EXIF coordinates are stored as ratio (num, den). Deal with possible 0 denominator
    d_deg = d[0] / d[1] if d[1] != 0 else 0
    m_deg = m[0] / m[1] if m[1] != 0 else 0
    s_deg = s[0] / s[1] if s[1] != 0 else 0
    return d_deg + (m_deg / 60.0) + (s_deg / 3600.0)

def extract_exif_metadata(file_bytes: bytes) -> Dict[str, Any]:
    """
    Extracts EXIF metadata from raw image bytes.
    Currently extracts Date Taken string and latitude/longitude floats, if present.
    """
    metadata = {}
    
    try:
        # Load the image from bytes without saving to disk
        img = Image.open(io.BytesIO(file_bytes))
        
        # Verify if 'exif' information is embedded inside the image info
        if "exif" not in img.info:
            return metadata
            
        exif_dict = piexif.load(img.info["exif"])
        
        # Attempt to extract Date Time Original
        if piexif.ExifIFD.DateTimeOriginal in exif_dict.get("Exif", {}):
            date_bytes = exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal]
            # PIEXIF usually returns bytes, decode it to string like '2023:01:01 12:00:00'
            metadata["date_taken"] = date_bytes.decode('utf-8')
            
        # Attempt to extract GPS Info
        gps_ifd = exif_dict.get("GPS", {})
        if gps_ifd:
            lat = gps_ifd.get(piexif.GPSIFD.GPSLatitude)
            lat_ref = gps_ifd.get(piexif.GPSIFD.GPSLatitudeRef)
            lon = gps_ifd.get(piexif.GPSIFD.GPSLongitude)
            lon_ref = gps_ifd.get(piexif.GPSIFD.GPSLongitudeRef)
            
            if lat and lat_ref and lon and lon_ref:
                # Ensure the references (N/S, E/W) are standard Python strings
                lat_ref_str = lat_ref.decode('utf-8') if isinstance(lat_ref, bytes) else lat_ref
                lon_ref_str = lon_ref.decode('utf-8') if isinstance(lon_ref, bytes) else lon_ref
                
                lat_val = _convert_to_degrees(lat)
                lon_val = _convert_to_degrees(lon)
                
                # Apply negative for South latitudes and West longitudes
                if lat_ref_str != "N":
                    lat_val = -lat_val
                if lon_ref_str != "E":
                    lon_val = -lon_val
                    
                metadata["latitude"] = round(lat_val, 6)
                metadata["longitude"] = round(lon_val, 6)

    except Exception as e:
        # On failure, simply return an empty or partial metadata dict
        # We don't want EXIF extraction to completely fail the image upload path
        print(f"Failed to extract EXIF data: {e}")
        
    return metadata
