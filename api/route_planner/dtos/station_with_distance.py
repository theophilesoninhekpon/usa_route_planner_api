from dataclasses import dataclass, field

from route_planner.models import FuelStation

@dataclass
class StationWithDistance:
    station: FuelStation
    distance_from_start: float

    @property
    def retail_price(self):
        return self.station.retail_price
    @property
    def latitude(self):
        return self.station.latitude
    @property
    def longitude(self):
        return self.station.longitude
    @property
    def id(self):
        return self.station.id
    