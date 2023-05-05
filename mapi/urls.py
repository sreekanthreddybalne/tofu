from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
# router.register('country', CountryViewSet, base_name='countries')

urlpatterns = router.urls

urlpatterns+=[
    path(r'location-autocomplete', LocationAutocompleteView.as_view()),
    path(r'reverse-geocode', ReverseGeocodeView.as_view()),
    path(r'distance-matrix', DistanceMatrixView.as_view()),
    path(r'nearby', NearbyView.as_view()),
    path(r'dishes', DishesView.as_view()),
    path(r'posts', PostsView.as_view()),
]
