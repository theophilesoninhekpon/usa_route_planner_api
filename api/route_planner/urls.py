from django.urls import include, path
from .views import RoutePlannerView, RouteMapView

urlpatterns = [
    path(
        'route',
        RoutePlannerView.as_view(),
        name='route_plan'),

        ]
