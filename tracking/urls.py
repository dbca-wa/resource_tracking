from django.urls import path
from tracking.views import DevicesView, HistoryView, RouteView


urlpatterns = [
    path('devices.csv', DevicesView.as_view(format='csv'), name='track_device_geojson'),
    path('devices.geojson', DevicesView.as_view(), name='track_device_geojson'),
    path('loggedpoint/<int:device_id>.geojson', HistoryView.as_view()),
    path('route/<int:device_id>.geojson', RouteView.as_view()),
]
