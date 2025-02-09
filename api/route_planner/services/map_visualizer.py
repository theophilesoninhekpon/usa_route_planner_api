import os
from pathlib import Path
from typing import List, Dict, Tuple
import uuid
from api import settings
import folium
from folium import plugins

class MapVisualizer:
    def __init__(self, route_points: List[Tuple[float, float]], fuel_stops: List[Dict]):
        self.route_points = route_points
        self.fuel_stops = fuel_stops
        self.maps_directory = os.path.join(settings.MEDIA_ROOT, 'route_maps')
        Path(self.maps_directory).mkdir(parents=True, exist_ok=True)
        
    def create_map(self) -> str:
        """Creates an interactive map with route and fuel stops"""
        # Center the map on the first point of the route
        start_point = self.route_points[0]
        route_map = folium.Map(location=start_point, zoom_start=6)
        
        # add itinerary
        route_coords = [[lat, lon] for lat, lon in self.route_points]
        folium.PolyLine(
            route_coords,
            weight=2,
            color='blue',
            opacity=0.8
        ).add_to(route_map)
        
        # Add start and end markers
        folium.Marker(
            route_coords[0],
            popup='Departure',
            icon=folium.Icon(color='green', icon='info-sign')
        ).add_to(route_map)
        
        folium.Marker(
            route_coords[-1],
            popup='Arrival',
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(route_map)
        
        # Add stations
        for stop in self.fuel_stops:
            station = stop['station']
            
            fuel_for_finish_text = f"Fuel required to finish the route: {stop['fuel_for_finish']:.1f} g" if 'fuel_for_finish' in stop else ""
            
            popup_content = f"""
                <b>{station['name']}</b><br>
                Price: {station['retail_price']}$<br>
                Distance: {stop['distance_from_start']:.1f} miles<br>
                Fuel needed: {stop['fuel_needed']:.1f} g<br>
                Cost: {stop['cost']:.2f}$<br>
                {fuel_for_finish_text}
            """.strip()
            
            point = [float(station['latitude']), float(station['longitude'])]
            
            
            folium.Marker(
                location=point,
                popup=popup_content,
                icon=folium.Icon(color='orange', icon='gas')
            ).add_to(route_map)
            
        # Add a minimap
        
        minimap = plugins.MiniMap()
        route_map.add_child(minimap)
        
        folium.LayerControl().add_to(route_map)

        filename = f"route_map_{uuid.uuid4().hex[:8]}.html"
        filepath = os.path.join(self.maps_directory, filename)
        
        # save map
        route_map.save(filepath)
        
        # return map url
        return f"{settings.API_URL}/media/route_maps/{filename}"
        