from django.utils.translation import gettext as _
from rest_framework import viewsets, status
from rest_framework import permissions
from rest_framework import filters
from django.http import Http404
from django.contrib.auth import authenticate, get_user_model, login
from rest_framework import serializers, generics
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from django.core.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_list_or_404, get_object_or_404
from django.db import transaction
from django.db.models import Q, Count, Case, When, FloatField, F, ExpressionWrapper
from django.db.models.expressions import Window
from django.db.models.functions import RowNumber
from django.utils import timezone
from datetime import timedelta
from itertools import groupby
from operator import attrgetter, itemgetter
from app.models import *
from .serializers import *
import api.permissions as custom_permissions
from .filters import CustomFilterBackend, CustomSearchFilter, MessageFilterBackend, ProspectFilterBackend
from .utils import appBasicAuthentication, CustomPagination

from rest_framework import serializers
from rest_framework import exceptions
from rest_framework_jwt.serializers import VerifyJSONWebTokenSerializer
from rest_framework.pagination import PageNumberPagination

from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import GeometryDistance, Distance
import app.choices as choices

#class CSVFileUploadView(generics.ListCreateAPIView):

class BaseAPIView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get_serializer_context(self):
        data = {}
        user = self.request.user
        if user and not user.is_authenticated:
            user = User.objects.get(phone_number="AnonymousUser")
        data['user'] = user
        data['view'] = self
        return data

class FileUploadView(BaseAPIView):

    def post(self, request, format=None):
        context = self.get_serializer_context()
        serializer = FileUploadSerializer(data=request.data, context=context)
        if serializer.is_valid():
            r = serializer.save()
            return Response(r)
        raise serializers.ValidationError(serializer.errors)

class SearchView(BaseAPIView, CustomPagination):
    permission_classes = (permissions.IsAuthenticated,)
    pagination_class = CustomPagination

    def get(self, request):
        query = request.query_params.get("query", None)
        type = request.query_params.get("type", None)
        if not query:
            raise serializers.ValidationError("No query")
        context = self.get_serializer_context()
        queryset = []
        if type == "dish":
            queryset = Dish.objects.filter(name__icontains=query)
        elif type == "restaurant":
            queryset = Restaurant.objects.filter(name__icontains=query)
        elif type == "user":
            queryset = User.objects.filter(name__icontains=query, username__icontains=query)
        else:
            dishes = Dish.objects.filter(name__icontains=query)
            restaurants = Restaurant.objects.filter(name__icontains=query)
            foodies = User.objects.filter(name__icontains=query, username__icontains=query)
            queryset = list(itertools.chain(dishes, restaurants, foodies))
        results = self.paginate_queryset(queryset, request, view=self)
        serializer = SearchSerializer(results, many=True, context=context)
        return self.get_paginated_response(serializer.data)

class FollowView(BaseAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        context = self.get_serializer_context()
        serializer = FollowSerializer(data=request.data, context=context)
        if serializer.is_valid():
            r = serializer.save()
            return Response(r)
        raise serializers.ValidationError(serializer.errors)

class FavouriteDishView(BaseAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        context = self.get_serializer_context()
        serializer = FavouriteDishSerializer(data=request.data, context=context)
        if serializer.is_valid():
            r = serializer.save()
            return Response(r)
        raise serializers.ValidationError(serializer.errors)

class LikePostView(BaseAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        context = self.get_serializer_context()
        serializer = LikePostSerializer(data=request.data, context=context)
        if serializer.is_valid():
            r = serializer.save()
            return Response(r)
        raise serializers.ValidationError(serializer.errors)

class LikePostCommentView(BaseAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        context = self.get_serializer_context()
        serializer = LikePostCommentSerializer(data=request.data, context=context)
        if serializer.is_valid():
            r = serializer.save()
            return Response(r)
        raise serializers.ValidationError(serializer.errors)

from django.http import HttpResponse
from wsgiref.util import FileWrapper
from django.core.files.uploadedfile import InMemoryUploadedFile
import zipfile
from io import StringIO
import csv


class BaseFileGenerateView(APIView):
    permission_classes = (permissions.AllowAny,)
    serializer = BaseFileGenerateSerializer

    def get_serializer_context(self):
        data = {}
        user = self.request.user
        if user and not user.is_authenticated:
            user = User.objects.get(phone_number="AnonymousUser")
        data['user'] = user
        data['view'] = self
        return data

    def post(self, request, format=None):
        context = self.get_serializer_context()
        serializer = self.serializer(data=request.data, context=context)
        if serializer.is_valid():
            file = serializer.save()
        else:
            return Response(serializer.errors)
        file_name = timezone.localtime().strftime("%Y%m%d%H%m%s_")+file.name
        response = HttpResponse(file.read(), content_type=file.content_type)
        response['Content-Disposition'] = 'attachment; filename='+file_name
        response['Content-Length'] = file.tell()
        return response

class FileGenerateView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get_serializer_context(self):
        data = {}
        user = self.request.user
        if user and not user.is_authenticated:
            user = User.objects.get(phone_number="AnonymousUser")
        data['user'] = user
        data['view'] = self
        return data

    def post(self, request, format=None):
        context = self.get_serializer_context()
        serializer = FileGenerateSerializer(data=request.data, context=context)
        if serializer.is_valid():
            file = serializer.save()
        else:
            return Response(serializer.errors)
        file_name = timezone.localtime().strftime("%Y%m%d%H%m%s_")+file.name
        response = HttpResponse(file.read(), content_type=file.content_type)
        response['Content-Disposition'] = 'attachment; filename='+file_name
        response['Content-Length'] = file.tell()
        return response




class LoginView(APIView):
    permission_classes = (permissions.AllowAny,)
    def post(self, request, format=None):
        data = request.data
        request.session.flush()
        username = data.get('username', None)
        password = data.get('password', None)

        if not username or not password:
            raise exceptions.AuthenticationFailed(_('No credentials provided.'))

        user = authenticate(username=username, password=password)

        if not user:
            raise exceptions.AuthenticationFailed(_('Invalid username/password.'))

        if not user.is_active:
            raise exceptions.AuthenticationFailed(_('User inactive or deleted.'))

        login(request, user)
        return Response("Logged In")

class AuthenticationView(APIView):
    authentication_classes = (SessionAuthentication, appBasicAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, format=None):
        content = {
            'user': request.user,
            'auth': request.auth,  # None
        }
        return Response(AuthUserSerializer(request.user).data)

class DeleteTokenView(APIView):
    permission_classes = (permissions.AllowAny,)
    def post(self, request, format=None):
        if request.user.is_authenticated:
            token = request.META.get('HTTP_AUTHORIZATION',' ').split(" ")[1]
            if token is not None:
                TokenBlackList.objects.create(token=token)
                return Response(True)
        return Response(False)

class AuthUserView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    def post(self, request, format=None):
        if request.user and request.user.is_authenticated:
            return Response(AuthUserSerializer(request.user).data)
        return Response(False)

class AuthUserReferralDataView(APIView):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    def get(self, request, format=None):
        if request.user.is_authenticated:
            return Response(ReferralDataSerializer(request.user.referral_data).data)
        raise Http404

class BaseActionsModelViewSet(viewsets.ModelViewSet):
    filter_backends = (CustomFilterBackend, CustomSearchFilter, filters.OrderingFilter,)
    ordering = ('-date_created',)
    class Meta:
        abstract = True

    def paginate_queryset(self, queryset):
        no_page = self.request.query_params.get('no_page', None)
        if no_page:
            return None
        return super().paginate_queryset(queryset)

    # @transaction.atomic
    def create(self, request, *args, **kwargs):
        is_many = True if isinstance(request.data, list) else False
        serializer = self.get_serializer(data=request.data, many=is_many)
        if serializer.is_valid():
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        else:
            if is_many:
                data={idx: er for idx, er in enumerate(serializer.errors)}
                raise serializers.ValidationError(data)
            else:
                raise serializers.ValidationError(serializer.errors)


    @transaction.atomic
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if hasattr(self.__class__, 'before_update') and callable(getattr(self.__class__, 'before_update')):
            self.before_update(request, instance, *args, **kwargs)
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def get_serializer_context(self):
        data = super().get_serializer_context()
        user = self.request.user
        if user and not user.is_authenticated:
            user = User.objects.get(phone_number="AnonymousUser")
        data['user'] = user
        data['view'] = self
        return data

    def get_serializer_class(self):
        assert self.serializer_class is not None, (
            "'%s' should either include a `serializer_class` attribute, "
            "or override the `get_serializer_class()` method."
            % self.__class__.__name__
        )
        if hasattr(self, 'admin_action_serializers') and self.request.user.is_superuser:
            if self.action in self.admin_action_serializers:
                return self.admin_action_serializers[self.action]

        if hasattr(self, 'self_action_serializers') and self.request.user and self.request.user.is_authenticated:
            if self.action in self.self_action_serializers:
                obj=self.get_object()
                if isinstance(obj, User):
                    if obj == self.request.user:
                        return self.self_action_serializers[self.action]

        if hasattr(self, 'auth_action_serializers') and self.request.user.is_authenticated:
            if self.action in self.auth_action_serializers:
                return self.auth_action_serializers[self.action]

        if hasattr(self, 'action_serializers'):
            if self.action in self.action_serializers:
                return self.action_serializers[self.action]
        return self.serializer_class

    def get_permissions(self):
        assert self.permission_classes is not None, (
            "'%s' should either include a `permission_classes` attribute, "
            "or override the `get_permissions()` method."
            % self.__class__.__name__
        )
        if hasattr(self, 'action_permissions'):
            if self.action in self.action_permissions:
                return [permission() for permission in self.action_permissions[self.action]]
        return [permission() for permission in self.permission_classes]

class PasswordResetView(APIView):
    permission_classes = (permissions.AllowAny,)
    def post(self, request, format=None):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            user = User.objects.get(phone_number=serializer.data['phone_number'])
            user.set_password(serializer.data['password'])
            user.is_active=True
            user.save()
            return Response(True)
        raise serializers.ValidationError(serializer.errors)
        #return Response(serializer.errors)


class CountryViewSet(BaseActionsModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = (custom_permissions.OnlyAdminActionsPermission,)
    pagination_class = CustomPagination
    filter_fields = ('id', 'title',)
    search_fields = ('id', 'title',)
    ordering_fields = ('id', 'title',)
    pagination_class.page_size = 5
    action_serializers = {
        'list': CountrySerializer,
        'retrieve': CountryDETAILSerializer,
        'create': CountryCREATESerializer,
        'update': CountryCREATESerializer,
        'partial_update': CountryCREATESerializer
    }
    self_action_serializers = {
        'retrieve': CountrySerializer,
    }

class StateViewSet(BaseActionsModelViewSet):
    queryset = State.objects.all()
    serializer_class = StateSerializer
    permission_classes = (custom_permissions.OnlyAdminActionsPermission,)
    pagination_class = CustomPagination
    filter_fields = ('id', 'title', 'country__id', 'country__title')
    search_fields = ('id', 'title', 'country__id', 'country__title')
    ordering_fields = ('id', 'title', 'country__id', 'country__title')
    pagination_class.page_size = 5
    action_serializers = {
        'list': StateSerializer,
        'retrieve': StateDETAILSerializer,
        'create': StateCREATESerializer,
        'update': StateCREATESerializer,
        'partial_update': StateCREATESerializer
    }
    self_action_serializers = {
        'retrieve': StateSerializer,
    }

class CityViewSet(BaseActionsModelViewSet):
    queryset = City.objects.all()
    serializer_class = CitySerializer
    permission_classes = (custom_permissions.OnlyAdminActionsPermission,)
    pagination_class = CustomPagination
    filter_fields = ('id', 'title', 'state__id', 'state__title', 'state__country__title')
    search_fields = ('id', 'title', 'state__id', 'state__title', 'state__country__title')
    ordering_fields = ('id', 'title', 'state__id', 'state__title', 'state__country__title')
    pagination_class.page_size = 5
    action_serializers = {
        'list': CitySerializer,
        'retrieve': CityDETAILSerializer,
        'create': CityCREATESerializer,
        'update': CityCREATESerializer,
        'partial_update': CityCREATESerializer
    }
    self_action_serializers = {
        'retrieve': CitySerializer,
    }

class UserViewSet(BaseActionsModelViewSet):
    queryset = User.objects.all().exclude(phone_number="AnonymousUser")
    serializer_class = UserSerializer
    permission_classes = (custom_permissions.UserViewPermission,)
    pagination_class = CustomPagination
    filter_fields = ('id', 'username', 'follows', 'followers', 'date_created')
    search_fields = ('id', 'username', 'date_created')
    ordering_fields = ('id', 'username', 'date_created')
    pagination_class.page_size = 5
    action_serializers = {
        'list': UserLISTSerializer,
        'retrieve': UserDETAILSerializer,
        'create': UserCREATESerializer,
        'update': UserUPDATESerializer,
        'partial_update': UserUPDATESerializer
    }
    self_action_serializers = {
        'retrieve': AuthUserSerializer,
        'update': AuthUserPOSTSerializer,
        'partial_update': AuthUserPOSTSerializer,
    }

class OTPViewSet(BaseActionsModelViewSet):
    queryset = OTP.objects.all()
    serializer_class = UserSerializer
    permission_classes = (permissions.AllowAny, custom_permissions.DisableActionsPermission)
    pagination_class = CustomPagination
    pagination_class.page_size = 5
    disable_actions = ["GET", "PUT", "PATCH"]
    action_serializers = {
        'list': OTPSerializer,
        'retrieve': OTPSerializer,
        'create': OTPCREATESerializer
    }

class UserLocationViewSet(BaseActionsModelViewSet):
    queryset = UserLocation.objects.all()
    serializer_class = UserLocationSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filter_fields = ('id', 'user', 'is_saved')
    search_fields =  ('id',)
    ordering_fields = ('id',)
    pagination_class = CustomPagination
    pagination_class.page_size = 50
    action_serializers = {
        'list': UserLocationLISTSerializer,
        'retrieve': BadgeSerializer,
        'create': UserLocationCREATESerializer,
        'update': UserLocationUPDATESerializer,
        'partial_update': UserLocationPATCHSerializer,
        'destroy': UserLocationDELETESerializer
    }
    self_action_serializers = {
        'retrieve': UserLocationSerializer,
    }

class BadgeViewSet(BaseActionsModelViewSet):
    queryset = Badge.objects.all()
    serializer_class = BadgeSerializer
    permission_classes = (custom_permissions.OnlyAdminActionsPermission,)
    filter_fields = ('id',)
    search_fields =  ('id',)
    ordering_fields = ('id',)
    pagination_class = CustomPagination
    pagination_class.page_size = 50
    action_serializers = {
        'list': BadgeSerializer,
        'retrieve': BadgeSerializer,
        'create': BadgeSerializer,
        'update': BadgeSerializer,
        'partial_update': BadgeSerializer
    }
    self_action_serializers = {
        'retrieve': BadgeSerializer,
    }

class ProviderViewSet(BaseActionsModelViewSet):
    queryset = Provider.objects.filter().order_by('?')
    serializer_class = ProviderSerializer
    permission_classes = (custom_permissions.OnlyAdminActionsPermission,)
    filter_fields = ('id', 'name', 'url',)
    search_fields =  ('id', 'name', 'url')
    ordering_fields = ('id', 'name', 'url')
    pagination_class = CustomPagination
    pagination_class.page_size = 50
    action_serializers = {
        'list': ProviderSerializer,
        'retrieve': ProviderSerializer,
        'create': ProviderSerializer,
        'update': ProviderSerializer,
        'partial_update': ProviderSerializer
    }
    self_action_serializers = {
        'retrieve': ProviderSerializer,
    }

class RestaurantViewSet(BaseActionsModelViewSet):
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer
    permission_classes = (custom_permissions.OnlyAdminActionsPermission,)
    filter_fields = ('id', 'name',)
    search_fields =  ('id', 'name',)
    ordering_fields = ('id', 'name',)
    pagination_class = CustomPagination
    pagination_class.page_size = 50
    action_serializers = {
        'list': RestaurantLISTSerializer,
        'retrieve': RestaurantDETAILSerializer,
        'create': RestaurantCREATESerializer,
        'update': RestaurantUPDATESerializer,
        'partial_update': RestaurantPATCHSerializer
    }
    self_action_serializers = {
        'retrieve': RestaurantSerializer,
    }

class RestaurantFileViewSet(BaseActionsModelViewSet):
    queryset = RestaurantFile.objects.all()
    serializer_class = RestaurantFileSerializer
    permission_classes = (permissions.AllowAny,)
    filter_fields = ('id', 'restaurant', 'restaurant__id')
    search_fields =  ('id',)
    ordering_fields = ('id',)
    pagination_class = CustomPagination
    pagination_class.page_size = 50
    action_serializers = {
        'list': RestaurantFileSerializer,
        'retrieve': RestaurantFileSerializer,
        'create': RestaurantFileSerializer,
        'update': RestaurantFileSerializer,
        'partial_update': RestaurantFileSerializer
    }
    self_action_serializers = {
        'retrieve': RestaurantFileSerializer,
    }

class RestaurantRatingTypeViewSet(BaseActionsModelViewSet):
    queryset = RestaurantRatingType.objects.all()
    serializer_class = RestaurantRatingTypeSerializer
    permission_classes = (permissions.AllowAny,)
    filter_fields = ('id',)
    search_fields =  ('id',)
    ordering_fields = ('id',)
    pagination_class = CustomPagination
    pagination_class.page_size = 50
    action_serializers = {
        'list': RestaurantRatingTypeSerializer,
        'retrieve': RestaurantRatingTypeSerializer,
        'create': RestaurantRatingTypeSerializer,
        'update': RestaurantRatingTypeSerializer,
        'partial_update': RestaurantRatingTypeSerializer
    }
    self_action_serializers = {
        'retrieve': RestaurantRatingTypeSerializer,
    }

class RestaurantRatingViewSet(BaseActionsModelViewSet):
    queryset = RestaurantRating.objects.all()
    serializer_class = RestaurantRatingSerializer
    permission_classes = (permissions.AllowAny,)
    filter_fields = ('id',)
    search_fields =  ('id',)
    ordering_fields = ('id',)
    pagination_class = CustomPagination
    pagination_class.page_size = 50
    action_serializers = {
        'list': RestaurantRatingSerializer,
        'retrieve': RestaurantRatingSerializer,
        'create': RestaurantRatingSerializer,
        'update': RestaurantRatingSerializer,
        'partial_update': RestaurantRatingSerializer
    }
    self_action_serializers = {
        'retrieve': RestaurantRatingSerializer,
    }

class DishTagViewSet(BaseActionsModelViewSet):
    queryset = DishTag.objects.all()
    serializer_class = DishTagSerializer
    permission_classes = (custom_permissions.OnlyAdminActionsPermission,)
    filter_fields = ('id',)
    search_fields =  ('id',)
    ordering_fields = ('id',)
    pagination_class = CustomPagination
    pagination_class.page_size = 50
    action_serializers = {
        'list': DishTagSerializer,
        'retrieve': DishTagSerializer,
        'create': DishTagSerializer,
        'update': DishTagSerializer,
        'partial_update': DishTagSerializer
    }
    self_action_serializers = {
        'retrieve': DishTagSerializer,
    }

class DishViewSet(BaseActionsModelViewSet):
    queryset = Dish.objects.all()
    serializer_class = DishSerializer
    permission_classes = (custom_permissions.OnlyAdminActionsPermission,)
    filter_fields = ('id', 'restaurant', 'restaurant__id', 'diet')
    search_fields =  ('id', 'name')
    ordering_fields = ('id', 'distance', 'score')
    ordering = None
    pagination_class = CustomPagination
    pagination_class.page_size = 50
    action_serializers = {
        'list': DishLISTSerializer,
        'retrieve': DishDETAILSerializer,
        'create': DishCREATESerializer,
        'update': DishUPDATESerializer,
        'partial_update': DishPATCHSerializer,
        'destroy': DishDELETESerializer
    }
    self_action_serializers = {
        'retrieve': DishSerializer,
    }

    def get_queryset(self):
        ds = DataStore.objects.all()[0]
        lat  = self.request.query_params.get("lat", None)
        lng  = self.request.query_params.get("lng", None)
        max_distance = self.request.query_params.get('max_distance', None)
        apply_number_of_ratings_threshold = self.request.query_params.get("apply_threshold", False)
        position = None
        if lat and lng:
            position = Point(float(lat), float(lng), srid=4326)
        if apply_number_of_ratings_threshold:
            self.queryset = self.queryset.filter(Q(zomato_number_of_ratings__gte=ds.zomato_number_of_ratings_threshold) | Q(no_of_ratings__gt=0))
        if max_distance and position:
            self.queryset =  self.queryset.annotate(
                distance = Case(When(restaurant__lat=None, then=100000), default=Distance("restaurant__lat_lng", position)),
                score_ = ExpressionWrapper(
                    F('score') + ((max_distance-F("distance"))/max_distance)*ds.weightage_distance,output_field=FloatField())
            ).exclude(
                distance__gte = max_distance
            ).annotate(row_number=Window(expression=RowNumber(), partition_by=[F('restaurant')])).order_by('row_number', '-score_')
        elif position:
            self.queryset =  self.queryset.annotate(
                distance = Case(When(restaurant__lat=None, then=100000), default=Distance("restaurant__lat_lng", position)),
            ).annotate(row_number=Window(expression=RowNumber(), partition_by=[F('restaurant')])).order_by('row_number', '-score')
        return self.queryset


class DishRatingTypeViewSet(BaseActionsModelViewSet):
    queryset = DishRatingType.objects.all()
    serializer_class = DishRatingTypeSerializer
    permission_classes = (permissions.AllowAny,)
    filter_fields = ('id',)
    search_fields =  ('id',)
    ordering_fields = ('id',)
    pagination_class = CustomPagination
    pagination_class.page_size = 50
    action_serializers = {
        'list': DishRatingTypeSerializer,
        'retrieve': DishRatingTypeSerializer,
        'create': DishRatingTypeSerializer,
        'update': DishRatingTypeSerializer,
        'partial_update': DishRatingTypeSerializer
    }
    self_action_serializers = {
        'retrieve': DishRatingTypeSerializer,
    }

class DishRatingViewSet(BaseActionsModelViewSet):
    queryset = DishRating.objects.all()
    serializer_class = DishRatingSerializer
    permission_classes = (permissions.AllowAny,)
    filter_fields = ('id',)
    search_fields =  ('id',)
    ordering_fields = ('id',)
    pagination_class = CustomPagination
    pagination_class.page_size = 50
    action_serializers = {
        'list': DishRatingSerializer,
        'retrieve': DishRatingSerializer,
        'create': DishRatingSerializer,
        'update': DishRatingSerializer,
        'partial_update': DishRatingSerializer
    }
    self_action_serializers = {
        'retrieve': DishRatingSerializer,
    }

class TagViewSet(BaseActionsModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (custom_permissions.OnlyAdminActionsPermission,)
    filter_fields = ('id',)
    search_fields =  ('id',)
    ordering_fields = ('id',)
    pagination_class = CustomPagination
    pagination_class.page_size = 50
    action_serializers = {
        'list': TagSerializer,
        'retrieve': TagSerializer,
        'create': TagSerializer,
        'update': TagSerializer,
        'partial_update': TagSerializer
    }
    self_action_serializers = {
        'retrieve': TagSerializer,
    }

class DishCollectionViewSet(BaseActionsModelViewSet):
    queryset = DishCollection.objects.all()
    serializer_class = DishCollectionSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    filter_fields = ('id', 'user')
    search_fields =  ('id',)
    ordering_fields = ('id',)
    pagination_class = CustomPagination
    pagination_class.page_size = 50
    action_serializers = {
        'list': DishCollectionLISTSerializer,
        'retrieve': DishCollectionDETAILSerializer,
        'create': DishCollectionCREATESerializer,
        'update': DishCollectionUPDATESerializer,
        'partial_update': DishCollectionPATCHSerializer
    }

    def destroy(self, request, pk):
        user = request.user
        q = DishCollection.objects.filter(pk=pk)
        if (not q.exists()) or (not user.is_authenticated) or (not user==q[0].user) :
            raise serializers.ValidationError("You are not authorized.")
        return super().destroy(request, *args, **kwargs)

from rest_framework.parsers import JSONParser, FormParser, MultiPartParser

class PostViewSet(BaseActionsModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    parser_classes = [JSONParser, MultiPartParser]
    filter_fields = ('id', 'user', 'user__id', 'dish', 'dish__id')
    search_fields =  ('id',)
    ordering_fields = ('id',)
    pagination_class = CustomPagination
    pagination_class.page_size = 50
    action_serializers = {
        'list': PostLISTSerializer,
        'retrieve': PostDETAILSerializer,
        'create': PostCREATESerializer,
        'update': PostUPDATESerializer,
        'partial_update': PostPATCHSerializer,
        'destroy': PostDELETESerializer,
    }
    self_action_serializers = {
        'retrieve': PostDETAILSerializer,
    }

class PostActivityViewSet(BaseActionsModelViewSet):
    post_content_type = ContentType.objects.get_for_model(Post)
    queryset = Activity.objects.filter(content_type=post_content_type)
    serializer_class = PostActivitySerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    filter_fields = ('id', 'object_id', 'activity_type')
    search_fields =  ('id',)
    ordering_fields = ('id',)
    pagination_class = CustomPagination
    pagination_class.page_size = 50
    action_serializers = {
        'list': PostActivityDETAILSerializer,
        'retrieve': PostActivityDETAILSerializer,
        'create': PostActivityCREATESerializer,
        'update': PostActivitySerializer,
        'partial_update': PostActivitySerializer,
        'destroy': PostActivitySerializer,
    }
    self_action_serializers = {
        'retrieve': PostActivitySerializer,
    }

class PostFileViewSet(BaseActionsModelViewSet):
    queryset = PostFile.objects.all()
    serializer_class = PostFileSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    filter_fields = ('id',)
    search_fields =  ('id',)
    ordering_fields = ('id',)
    pagination_class = CustomPagination
    pagination_class.page_size = 50
    action_serializers = {
        'list': PostFileLISTSerializer,
        'retrieve': PostFileDETAILSerializer,
        'create': PostFileCREATESerializer,
        'update': PostFileUPDATESerializer,
        'partial_update': PostFilePATCHSerializer,
        'destroy': PostFileDELETESerializer,
    }
    self_action_serializers = {
        'retrieve': PostFileDETAILSerializer,
    }

class PostCommentViewSet(BaseActionsModelViewSet):
    queryset = PostComment.objects.all()
    serializer_class = PostCommentSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    filter_fields = ('id', 'post')
    search_fields =  ('id',)
    ordering_fields = ('id',)
    pagination_class = CustomPagination
    pagination_class.page_size = 50
    action_serializers = {
        'list': PostCommentLISTSerializer,
        'retrieve': PostCommentDETAILSerializer,
        'create': PostCommentCREATESerializer,
        'update': PostCommentUPDATESerializer,
        'partial_update': PostCommentPATCHSerializer,
        'destroy': PostCommentDELETESerializer
    }
    self_action_serializers = {
        'retrieve': PostCommentSerializer,
    }


class PostCommentActivityViewSet(BaseActionsModelViewSet):
    post_comment_content_type = ContentType.objects.get_for_model(PostComment)
    queryset = Activity.objects.filter(content_type=post_comment_content_type)
    serializer_class = PostCommentActivitySerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    filter_fields = ('id', 'object_id', 'activity_type')
    search_fields =  ('id',)
    ordering_fields = ('id',)
    pagination_class = CustomPagination
    pagination_class.page_size = 50
    action_serializers = {
        'list': PostCommentActivityDETAILSerializer,
        'retrieve': PostCommentActivityDETAILSerializer,
        'create': PostCommentActivityCREATESerializer,
        'update': PostCommentActivitySerializer,
        'partial_update': PostCommentActivitySerializer,
        'destroy': PostCommentActivitySerializer,
    }
    self_action_serializers = {
        'retrieve': PostCommentActivitySerializer,
    }

class ActivityViewSet(BaseActionsModelViewSet):
    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer
    permission_classes = (permissions.IsAuthenticated,)
    filter_fields = ('id',)
    search_fields =  ('id',)
    ordering_fields = ('id',)
    pagination_class = CustomPagination
    pagination_class.page_size = 50
    action_serializers = {
        'list': ActivitySerializer,
        'retrieve': ActivitySerializer,
        'create': ActivitySerializer,
        'update': ActivitySerializer,
        'partial_update': ActivitySerializer
    }
    self_action_serializers = {
        'retrieve': ActivitySerializer,
    }

class DataStoreViewSet(BaseActionsModelViewSet):
    queryset = DataStore.objects.all()
    serializer_class = DataStoreSerializer
    permission_classes = (custom_permissions.OnlyAdminPermission,)
    filter_fields = ('id',)
    search_fields =  ('id',)
    ordering_fields = ('id',)
    ordering = None
    pagination_class = CustomPagination
    pagination_class.page_size = 50
    disable_actions = ["POST"]
    action_serializers = {
        'list': DataStoreSerializer,
        'retrieve': DataStoreSerializer,
        'create': DataStoreSerializer,
        'update': DataStoreSerializer,
        'partial_update': DataStoreSerializer,
        'destroy': DataStoreSerializer
    }

class FeedbackViewSet(BaseActionsModelViewSet):
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = (permissions.IsAuthenticated,)
    filter_fields = ('id',)
    search_fields =  ('id',)
    ordering_fields = ('id',)
    ordering = None
    pagination_class = CustomPagination
    pagination_class.page_size = 50
    action_serializers = {
        'list': FeedbackLISTSerializer,
        'retrieve': FeedbackDETAILSerializer,
        'create': FeedbackCREATESerializer,
        'update': FeedbackUPDATESerializer,
        'partial_update': FeedbackPATCHSerializer
    }
