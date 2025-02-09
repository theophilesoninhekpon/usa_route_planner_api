from django.db import models

from django.db import models
from decimal import Decimal

class FuelStation(models.Model):
    opis_id = models.IntegerField()
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=2)
    rack_id = models.IntegerField()
    retail_price = models.DecimalField(max_digits=10, decimal_places=8)
    latitude = models.DecimalField(max_digits=10, decimal_places=6, null=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=6, null=True)

    def __str__(self):
        return f"{self.name} - {self.city}, {self.state}"

    class Meta:
        indexes = [
            models.Index(fields=['state']),
            models.Index(fields=['retail_price']),
        ]