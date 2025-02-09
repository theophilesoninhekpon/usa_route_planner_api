from django.http import JsonResponse
from django.shortcuts import render
from route_planner.services.map_visualizer import MapVisualizer
from rest_framework.views import APIView
from route_planner.serializers import RouteRequestSerializer, RouteResponseSerializer
from route_planner.services.routing import RoutePlanner
from rest_framework import status
from django.views.generic import TemplateView



class RouteMapView(TemplateView):
    template_name = 'route_map.html'

class RoutePlannerView(APIView):
    def post(self, request):
        serializer = RouteRequestSerializer(data=request.data)
        if serializer.is_valid():
            try: 
                planner = RoutePlanner(
                    start_location=serializer.validated_data['start_location'],
                    end_location=serializer.validated_data['end_location']
                )
                route_data = planner.plan_route()

                response_serializer = RouteResponseSerializer(data=route_data)
                if response_serializer.is_valid():
                    
                    # create route map
                    visualizer = MapVisualizer(response_serializer.data['route'], response_serializer.data['fuel_stops'])
                    map_url = visualizer.create_map()
                    
                    
                    return JsonResponse({
                        'status': 'success',
                        'data': {'content': response_serializer.data, 'map_url': map_url}
                    },  status=status.HTTP_200_OK)
                return JsonResponse(response_serializer.errors, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            except Exception as e:
                return JsonResponse(
                    {'error': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)