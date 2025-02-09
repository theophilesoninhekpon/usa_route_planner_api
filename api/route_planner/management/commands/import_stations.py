from decimal import Decimal
import time
from django.core.management.base import BaseCommand
from geopy.geocoders import Nominatim, ArcGIS
from geopy.exc import GeocoderTimedOut
import csv

from route_planner.models import FuelStation

class Command(BaseCommand):
    help = "Import fuel stations from CSV file"

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help="Path to the CSV file")


    def handle(self, *args, **options):
        # geolocator = Nominatim(user_agent="fuel_route_planner")
        geolocator = ArcGIS(timeout=10)
        
        count = 0

        with open(options['csv_file'], 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                count = count + 1
                # we sanitize data
                price = row['Retail Price'].replace(',', '.')

                if not FuelStation.objects.filter(
                    name=row['Truckstop Name'].strip(),
                    retail_price=Decimal(price),
                    address=row['Address'].strip(),
                    city=row['City'].strip(),
                    state=row['State'].strip(),
                    rack_id=int(row['Rack ID']),
                    ).exists():

                    station = FuelStation(
                        opis_id=int(row['OPIS Truckstop ID'].strip()),
                        name=row['Truckstop Name'].strip(),
                        address=row['Address'].strip(),
                        city=row['City'].strip(),
                        state=row['State'].strip(),
                        rack_id=int(row['Rack ID']),
                        retail_price=Decimal(price)
                    )

                    # We'll geocode adress
                    try:
                        address = f"{station.address}, {station.city}, {station.state}, USA"
                        location = geolocator.geocode(address, timeout=5)
                      
                        if location:
                            station.latitude = location.latitude
                            station.longitude = location.longitude

                    except GeocoderTimedOut:
                        self.stdout.write(self.style.WARNING(
                            f"Timeout fpr {station.name}"
                        ))
                    
                    station.save()

                    self.stdout.write(self.style.SUCCESS(
                        f"Station {count} imported: {station.name}"
                    ))