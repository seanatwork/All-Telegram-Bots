import requests
from typing import List, Dict, Tuple
from gotwater_config import Config

class MapGenerator:
    def __init__(self):
        self.api_key = Config.GOOGLE_MAPS_API_KEY
        self.base_url = "https://maps.googleapis.com/maps/api/staticmap"
    
    def generate_static_map(self, user_lat: float, user_lon: float, 
                          fountains: List[Dict]) -> bytes:
        """
        Generate a static map image with user location and water fountains.
        
        Args:
            user_lat: User's latitude
            user_lon: User's longitude
            fountains: List of fountain dictionaries
            
        Returns:
            Map image as bytes
        """
        if not fountains:
            # Generate map with just user location
            params = {
                'center': f'{user_lat},{user_lon}',
                'zoom': 15,
                'size': '600x400',
                'markers': f'color:blue|{user_lat},{user_lon}',
                'key': self.api_key
            }
        else:
            # Generate map with user location and fountains
            markers = []
            
            # Add user marker (blue)
            markers.append(f'color:blue|{user_lat},{user_lon}')
            
            # Add fountain markers (red)
            for fountain in fountains[:10]:  # Limit to 10 fountains for clarity
                markers.append(f'color:red|{fountain["latitude"]},{fountain["longitude"]}')
            
            params = {
                'center': f'{user_lat},{user_lon}',
                'zoom': 15,
                'size': '600x400',
                'markers': markers,
                'key': self.api_key
            }
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"Error generating static map: {e}")
            return b''
    
    def generate_google_maps_links(self, user_lat: float, user_lon: float,
                                fountains: List[Dict]) -> List[str]:
        """
        Generate Google Maps navigation links for water fountains.
        
        Args:
            user_lat: User's latitude
            user_lon: User's longitude
            fountains: List of fountain dictionaries
            
        Returns:
            List of Google Maps URLs
        """
        links = []
        
        for fountain in fountains[:5]:  # Limit to 5 closest fountains
            # Create navigation link from user location to fountain
            nav_url = (f"https://www.google.com/maps/dir/"
                      f"{user_lat},{user_lon}/"
                      f"{fountain['latitude']},{fountain['longitude']}")
            
            # Add distance info to link text
            distance_text = f"{fountain['distance']:.0f}m"
            fountain_name = fountain['name']
            
            # Add emoji based on water source type
            type_emoji = {
                'drinking_water': '🚰',
                'water_point': '💧',
                'water': '💦',
                'water_well': '🏺',
                'restroom': '🚽',
                'toilets': '🚽',
                'unknown': '📍'
            }.get(fountain.get('type', 'unknown'), '📍')
            
            link_text = f"{type_emoji} {fountain_name} ({distance_text})"
            links.append(f"[{link_text}]({nav_url})")
        
        return links
    
    def generate_search_area_link(self, user_lat: float, user_lon: float) -> str:
        """
        Generate a Google Maps link showing the search area.
        
        Args:
            user_lat: User's latitude
            user_lon: User's longitude
            
        Returns:
            Google Maps URL for the search area
        """
        return (f"https://www.google.com/maps/search/"
                f"drinking+water/@{user_lat},{user_lon},15z")
