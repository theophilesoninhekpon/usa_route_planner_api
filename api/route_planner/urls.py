from django.urls import include, path
from .views import RoutePlannerView, RouteMapView

urlpatterns = [
    path(
        'map',
        RouteMapView.as_view(),
        name='route_map'),
    path(
        'route',
        RoutePlannerView.as_view(),
        name='route_plan'),

        ]
