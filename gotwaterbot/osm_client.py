import overpy
import math
import time
import random
from typing import List, Dict, Optional

class OSMClient:
    def __init__(self):
        self.api = overpy.Overpass()
    
    def find_water_fountains(self, latitude: float, longitude: float, radius: int = 1000) -> List[Dict]:
        """
        Find water fountains within specified radius of given coordinates.
        
        Args:
            latitude: User's latitude
            longitude: User's longitude  
            radius: Search radius in meters (default 1000)
            
        Returns:
            List of dictionaries containing fountain information
        """
        # Enhanced query to find multiple types of water sources and restroom facilities
        query = f"""
        [out:json][timeout:25];
        (
          node["amenity"="drinking_water"](around:{radius},{latitude},{longitude});
          node["amenity"="water_point"](around:{radius},{latitude},{longitude});
          node["amenity"="water"](around:{radius},{latitude},{longitude});
          node["natural"="water"]["access"="public"](around:{radius},{latitude},{longitude});
          node["man_made"="water_well"]["access"="public"](around:{radius},{latitude},{longitude});
          node["amenity"="toilets"](around:{radius},{latitude},{longitude});
          node["amenity"="restroom"](around:{radius},{latitude},{longitude});
          node["building"="public_toilet"](around:{radius},{latitude},{longitude});
          way["amenity"="drinking_water"](around:{radius},{latitude},{longitude});
          way["amenity"="water_point"](around:{radius},{latitude},{longitude});
          way["amenity"="toilets"](around:{radius},{latitude},{longitude});
          way["amenity"="restroom"](around:{radius},{latitude},{longitude});
        );
        out body;
        >;
        out skel qt;
        """
        
        try:
            print(f"Querying OpenStreetMap around ({latitude}, {longitude}) with {radius}m radius")
            
            # Retry logic with exponential backoff
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    result = self.api.query(query)
                    break  # Success, exit retry loop
                except Exception as e:
                    if "Server load too high" in str(e) or "429" in str(e):
                        if attempt < max_retries - 1:
                            # Exponential backoff with jitter
                            wait_time = (2 ** attempt) + random.uniform(0, 1)
                            print(f"Server busy, retrying in {wait_time:.1f}s... (attempt {attempt + 1}/{max_retries})")
                            time.sleep(wait_time)
                            continue
                        else:
                            print(f"Failed after {max_retries} attempts: {e}")
                            return []
                    else:
                        # Other errors, don't retry
                        raise e
            
            fountains = []
            
            for node in result.nodes:
                # Determine the type and appropriate name
                tags = node.tags
                amenity = tags.get('amenity', '')
                building = tags.get('building', '')
                
                if amenity in ['drinking_water', 'water_point', 'water']:
                    facility_type = amenity
                    facility_name = tags.get('name', 'Water Fountain' if amenity == 'drinking_water' else 'Water Point')
                elif amenity in ['toilets', 'restroom'] or building == 'public_toilet':
                    facility_type = 'restroom'
                    facility_name = tags.get('name', 'Restroom (likely has water)')
                else:
                    facility_type = tags.get('natural', tags.get('man_made', 'unknown'))
                    facility_name = tags.get('name', 'Water Source')
                
                fountain_info = {
                    'id': node.id,
                    'name': facility_name,
                    'latitude': float(node.lat),
                    'longitude': float(node.lon),
                    'distance': self._calculate_distance(latitude, longitude, float(node.lat), float(node.lon)),
                    'type': facility_type
                }
                fountains.append(fountain_info)
                print(f"Found {facility_type}: {facility_name} at {fountain_info['distance']:.0f}m")
            
            # Sort by distance
            fountains.sort(key=lambda x: x['distance'])
            print(f"Total found: {len(fountains)} water sources and restrooms")
            return fountains
            
        except Exception as e:
            print(f"Error querying OpenStreetMap: {e}")
            return []
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points in meters using Haversine formula.
        """
        R = 6371000  # Earth's radius in meters
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
