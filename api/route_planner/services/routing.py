from decimal import Decimal
from typing import Dict, List, Tuple
from django.core.cache import cache
from route_planner.services.map_visualizer import MapVisualizer
from geopy.geocoders import Nominatim, ArcGIS
from geopy.distance import geodesic, Distance
import requests
from route_planner.serializers import FuelStationSerializer
from route_planner.dtos.station_with_distance import StationWithDistance
from route_planner.models import FuelStation


class RoutePlanner:
    def __init__(self, start_location: str, end_location: str, tank_range: float = 500.0, mpg: float = 10.0):
        """
        Initialize route planner with US-specific defaults
        tank_range: Range in miles
        mpg: Miles per gallon
        """
        self.start = start_location
        self.end = end_location
        self.tank_range = tank_range
        self.mpg = mpg
        self.OSRM_API_URL = "https://router.project-osrm.org/route/v1/driving/"
        self.geocoder = ArcGIS(timeout=10)


    def get_coordinates(self, location:str) -> Tuple[float, float]:
        """Converts address to coordinates using geopy's Nominatim"""
        cache_key = f"geocode_{location}"
        cached_coords = cache.get(cache_key)

        if cached_coords:
            return cached_coords
        
        location_with_country = f"{location}, United States"
        location_data = self.geocoder.geocode(
            location_with_country,
            exactly_one=True,
        )

        if not location_data:
            raise ValueError(f"Unable to geocode address: {location}")
        
        coords = (location_data.latitude, location_data.longitude)
        cache.set(cache_key, coords, 86400) # cache for 24h
        return coords

    def calculate_distance(self, point1: Tuple[float, float], point2:Tuple[float, float],) -> float:
        """Calculate distance between two points in miles using geopy"""
        return geodesic(point1, point2).miles
    

    def get_route(self) -> Dict:
        """Get route using OSRM"""
        cache_key = f"route_{self.start}_{self.end}"
        cached_route = cache.get(cache_key)

        if cached_route:
            return cached_route
        
        start_coords = self.get_coordinates(self.start)
        end_coords = self.get_coordinates(self.end)

        url = f"{self.OSRM_API_URL}{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}"
        params = {
            'overview': 'full',
            'geometries': 'geojson',
            'steps': 'false'
        }

        response = requests.get(url, params=params)
        route_data = response.json()

        if route_data.get('code') != 'Ok':
            raise ValueError("Error retrieving route")
        
        distance_meters = route_data['routes'][0]['distance']
        distance = Distance(meters=distance_meters).miles
        
        processed_route = {
            'route': {
                'distance': distance,
                'shape': {
                    'shapePoints': [
                        (coord[1], coord[0])
                        for coord in route_data['routes'][0]['geometry']['coordinates']
                    ]
                }
            }
        }

        cache.set(cache_key, processed_route, 8640)

        return processed_route

    def find_stations_near_route(self, route_points: List[Tuple[float, float]], route_distance: float, max_distance: float = 30.0) -> List[StationWithDistance]:
        """
        Find optimal gas stations near route when vehicle needs refueling (tank range = 500 miles)
        Returns stations close to points where remaining range gets low
        """
        stations_near_route = []
        all_stations = FuelStation.objects.all()
        current_distance = 0
        current_distance_from_start = 0
        
        # Calculate cumulative distance along route until we approach tank range
        for i in range(1, len(route_points)):
            segment_distance = self.calculate_distance(route_points[i-1], route_points[i])
            current_distance += segment_distance
            current_distance_from_start += segment_distance # the distance from start to current_point
            
            # When we get close to tank range limit (e.g. within 50 miles), look for stations if the route distance is great than the tank_range
            if current_distance >= (self.tank_range - 50) and route_distance > self.tank_range:  # Start looking before completely empty
                target_point = route_points[i]
                nearby_stations = []
                
                # Find all stations near this point
                for station in all_stations:
                    distance_to_station = self.calculate_distance(target_point, 
                                                            (station.latitude, station.longitude))
                    
                    if distance_to_station <= max_distance:
                        total_distance = current_distance_from_start + distance_to_station
                        station_with_distance = StationWithDistance(
                            station=station,
                            distance_from_start=total_distance
                        )
                        nearby_stations.append(station_with_distance)
                
                print('nearby_stations')
                print(nearby_stations)
                # Sort by price and get best option
                if nearby_stations:
                    nearby_stations.sort(key=lambda s: s.retail_price)
                    best_station = nearby_stations[0]
                    stations_near_route.append(best_station)

                # Reset distance counter from this new refueling point
                current_distance = 0
                
                    
        
        return stations_near_route
    
    
    def optimize_fuel_stops(self, route_distance: float, stations: list[StationWithDistance]) -> List[Dict]:
        """Calculate optimal fuel stops (all distances in miles)"""
        current_range = self.tank_range
        total_distance = 0
        optimal_stops = []
        current_position = 0

        while total_distance < route_distance:
            remaining_distance = route_distance - total_distance
            if remaining_distance <= current_range:
                if len(optimal_stops) > 0:
                    
                    last_station = optimal_stops[-1]
                    last_station['fuel_for_finish'] = remaining_distance / self.mpg
                    last_station['total_fuel'] = last_station['fuel_needed']
                    last_station['cost'] = (
                        Decimal(str(last_station['total_fuel'] + last_station['fuel_for_finish'])) * 
                        Decimal(str(last_station['station']['retail_price']))
                    ).quantize(Decimal('0.01'))
                break
            
            reachable_stations = [
                station for station in stations
                if station.distance_from_start <= current_position + current_range
                and station.distance_from_start > current_position
            ]

         

            if not reachable_stations:  
                
                """
                NOTICE: sometimes there are situations where there is no station 
                close to the road for a given interval, taking into account the 
                car's range and the maximum distance between the car and a station.
                When these situations arise, to avoid running out of fuel, the driver 
                will load the amount of fuel he will need for the interval (range) where 
                there is no nearby station onto the one taken from the previous station 
                found.
                """
                
                # get the fuel needed based on car's range
                if len(optimal_stops) > 0:
                    print('ici')
                    fuel_needed = self.tank_range / self.mpg
                    last_station = optimal_stops[-1]
                    print(last_station)
                    last_station['fuel_needed'] += fuel_needed
                    last_station['total_fuel'] = last_station['fuel_needed']
                    last_station['cost'] = (
                        Decimal(str(last_station['total_fuel'])) * 
                        Decimal(str(last_station['station']['retail_price']))
                    ).quantize(Decimal('0.01'))
                    
                # Because we don't find any station on the current_range, 
                # we add the tank_range to the total_distance and current_position      
                total_distance += self.tank_range
                current_position += self.tank_range
                current_range = self.tank_range   
                continue
            
            # we get the lowest cheap and near station
            best_station = min(
                reachable_stations,
                key= lambda s: float(s.retail_price) * (1 + ((s.distance_from_start - current_position) / self.tank_range))
            )
            print(best_station)

            if best_station:
                # calculate the fuel to load to reach this station from the previous station or from the start
                fuel_needed = (best_station.distance_from_start - current_position) / self.mpg 
                
                optimal_stops.append({
                    'station': FuelStationSerializer(best_station.station).data,
                    'distance_from_start': best_station.distance_from_start,
                    'fuel_needed': fuel_needed,
                    'total_fuel': fuel_needed,  
                    'cost': (Decimal(str(fuel_needed)) * Decimal(str(best_station.retail_price))).quantize(Decimal('0.01'))
                })

            total_distance += best_station.distance_from_start - current_position
            current_position = best_station.distance_from_start
            current_range = self.tank_range

        return optimal_stops
    

    def calculate_total_cost(self, fuel_stops: List[Dict]) -> Decimal:
        """Calculate total fuel cost for the route"""
        total = sum(stop['cost'] for stop in fuel_stops)
        return total.quantize(Decimal('0.01')) if isinstance(total, float) else total
    
    
    def plan_route(self) -> Dict:
        """Main entry point for route planning"""
        route_data = self.get_route()
        route_points = route_data['route']['shape']['shapePoints']
        total_distance = route_data['route']['distance']

        stations = self.find_stations_near_route(route_points, total_distance)
        fuel_stops = self.optimize_fuel_stops(total_distance, stations)
        total_cost = self.calculate_total_cost(fuel_stops)
     

        return {
            'route': route_points,
            'distance': total_distance,
            'fuel_stops': fuel_stops,
            'total_cost': total_cost
        }