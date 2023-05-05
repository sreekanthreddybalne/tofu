from django.utils.translation import gettext as _
from django.http import Http404
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import F, Func

from rest_framework import serializers, permissions, exceptions

import requests, json
import googlemaps
from datetime import datetime
from django.conf import settings
import googlemaps
from app.models import Post, Dish, DataStore
from api.serializers import PostLISTSerializer, DishLISTSerializer
from api.views import BaseAPIView
import math
from django.db.models import ExpressionWrapper, DecimalField, F, Avg, Count, Case, When, FloatField, Value
from decimal import Decimal
from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import GeometryDistance
gmaps = googlemaps.Client(key=settings.GOOGLE_API_KEY)

#class CSVFileUploadView(generics.ListCreateAPIView):

class LocationAutocompleteView(BaseAPIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        input_text = request.query_params.get("input_text", None)
        if not input_text:
            raise serializers.ValidationError("input_text is required")
        components = {"country": ["in"]}
        return Response(gmaps.places_autocomplete(input_text=input_text, components=components))

class NearbyView(BaseAPIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        lat = request.query_params.get("lat", None)
        lng = request.query_params.get("lng", None)
        type = request.query_params.get("type", "restaurant")
        keyword = request.query_params.get("keyword", "A")
        rank_by = request.query_params.get("rank_by", "distance")
        res = None
        if lat and lng:
            res = gmaps.places_nearby(location=(lat, lng), keyword=keyword, rank_by=rank_by, type=type)
        return Response(res)

class DistanceMatrixView(BaseAPIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        origins = request.query_params.get("origins", None)
        destinations = request.query_params.get("destinations", None)
        res = None
        if origins and destinations:
            res = gmaps.distance_matrix(origins=origins, destinations=destinations)
        return Response(res)

class ReverseGeocodeView(BaseAPIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        place_id = request.query_params.get("place_id", None)
        lat = request.query_params.get("lat", None)
        lng = request.query_params.get("lng", None)
        res = None
        if(place_id):
            res = gmaps.reverse_geocode(place_id)
        elif lat and lng:
            res = gmaps.reverse_geocode(latlng={"lat": lat, "lng": lng})
        return Response(res)


class DishesView(BaseAPIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        lat = request.query_params.get("lat", None)
        lng = request.query_params.get("lng", None)
        max_distance = request.query_params.get("max_distance", 10) #10 miles
        ds = DataStore.objects.get(pk=1)
        position = Point(float(lat), float(lng), srid=4326)
        q = Dish.objects.annotate(
                distance = Case(When(restaurant__lat=None, then=20), default=GeometryDistance("restaurant__lat_lng", position), output_field=FloatField()),
                rating_=Case(
                    When(rating=None, then=0), default=F('rating'), output_field=FloatField()
                ),
                posts_count = Count('posts', output_field=FloatField()),
                zomato_rating_=Case(
                    When(zomato_rating=None, then=0), default=F('zomato_rating'), output_field=FloatField()
                ),
                zomato_number_of_ratings_ = Case(
                    When(zomato_number_of_ratings=None, then=0), default=F('zomato_number_of_ratings'), output_field=FloatField()
                ),
                files_count = Count('files', output_field=FloatField())
                # price_=Case(
                #     When(price=None, then=avg_price*1.5), default=F('price'), output_field=FloatField()
                # )
            ).annotate(
                score = ((max_distance-F("distance"))/max_distance)*ds.weightage_distance +
                (F('rating_')*F('posts_count')/ds.max_tofu_popularity)*ds.weightage_tofu_popularity +
                (F('zomato_rating_')*F('zomato_number_of_ratings_')/ds.max_zomato_popularity)*ds.weightage_zomato_popularity
                # weightage["price"] - Func(weightage["price"]*((avg_price-F('price_'))/avg_price)/100, function="ABS")
            ).order_by("-score")[:10]
        context = self.get_serializer_context()
        print("score")
        print(q[0].score)
        data = DishLISTSerializer(instance=q, many=True, context=context).data
        return Response(data)

class PostsView(BaseAPIView):
    permission_classes = (permissions.AllowAny,)
