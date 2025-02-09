from rest_framework import serializers

from route_planner.models import FuelStation

class RouteRequestSerializer(serializers.Serializer):
    start_location = serializers.CharField()
    end_location = serializers.CharField()


class RouteResponseSerializer(serializers.Serializer):
    route = serializers.ListField()
    fuel_stops = serializers.ListField()
    total_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    distance = serializers.FloatField()

class FuelStationSerializer(serializers.ModelSerializer):

    class Meta:
        model = FuelStation
        fields = '__all__'
