from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class GeocodingClient:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="water-fountain-bot")
    
    def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Convert address string to latitude and longitude coordinates.
        Supports both US and UK address formats.
        
        Args:
            address: Street address string (e.g., "816 S Highland St, Arlington, VA 22204" or "221B Baker Street, London NW1 6XE")
            
        Returns:
            Tuple of (latitude, longitude) or None if geocoding fails
        """
        try:
            # First try with the original address
            location = self.geolocator.geocode(address, timeout=10)
            
            if location:
                logger.info(f"Geocoded '{address}' to ({location.latitude}, {location.longitude})")
                return (location.latitude, location.longitude)
            
            # If UK address fails, try adding "United Kingdom" for better results
            if any(uk_indicator in address.lower() for uk_indicator in ['london', 'uk', 'united kingdom', 'england', 'scotland', 'wales', 'northern ireland']):
                uk_address = f"{address}, United Kingdom"
                location = self.geolocator.geocode(uk_address, timeout=10)
                
                if location:
                    logger.info(f"Geocoded UK address '{uk_address}' to ({location.latitude}, {location.longitude})")
                    return (location.latitude, location.longitude)
            
            logger.warning(f"Could not geocode address: {address}")
            return None
                
        except GeocoderTimedOut:
            logger.error(f"Geocoding timed out for address: {address}")
            return None
        except GeocoderServiceError as e:
            logger.error(f"Geocoding service error for address '{address}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error geocoding address '{address}': {e}")
            return None
    
    def format_address_response(self, address: str, coordinates: Tuple[float, float]) -> str:
        """
        Format a response showing the geocoded address and coordinates.
        
        Args:
            address: Original address string
            coordinates: (latitude, longitude) tuple
            
        Returns:
            Formatted string for display
        """
        lat, lon = coordinates
        return f"📍 Address: {address}\n🗺️ Coordinates: {lat:.6f}, {lon:.6f}"
