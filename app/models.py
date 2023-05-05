from __future__ import unicode_literals
import os
import datetime
import random
from itertools import groupby
from operator import attrgetter, itemgetter
from rest_framework.authtoken.models import Token
from django.urls import reverse_lazy
# from django.db import models
from django.contrib.gis.db import models
from django.contrib.contenttypes.fields import GenericRelation, GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models import Sum, Count, Avg, Max, F, Q
from django.db.models.functions import Coalesce
from django.conf import settings
from django.contrib.auth.models import AbstractUser
import json, itertools
from django.core.validators import RegexValidator
from rest_framework.serializers import ValidationError
from django.utils.text import slugify
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from sorl.thumbnail import ImageField, get_thumbnail
from decimal import *
from .managers import UserManager
from .settings import *
import app.choices as choices
from . import custom_fields


class AppModel(models.Model):
    #is_deleted = models.BooleanField(default=False)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

def get_file_upload_path(instance, filename):
    return os.path.join('files/', timezone.localtime().date().strftime("%Y/%m/%d"), filename)

def get_photo_upload_path(instance, filename):
    return os.path.join('photos/', timezone.localtime().date().strftime("%Y/%m/%d"), filename)


def get_default_profile_photo():
    return 'default/profile/'+str(random.randint(1,25))+'.png'

def get_profile_photo_upload_path(instance, filename):
    return os.path.join('images/profile/', timezone.localtime().date().strftime("%Y/%m/%d"), filename)

COUNTRY_INDIA_ID = 115

class User(AppModel,AbstractUser):
    """This model defines the common fields among Admin, Marketing Manager, Advisor Manager, Advisor and Prospect.
    """
    email=None
    username = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=255, default=None, blank=True, null=True)
    gender = models.CharField(max_length=255, choices=choices.GENDER, default=choices.GENDER_MALE)
    photo = ImageField(upload_to=get_profile_photo_upload_path,default=get_default_profile_photo)
    #phone_regex = RegexValidator(regex=r'^([16789]\d{9}|AnonymousUser)$', message="Mobile No. is invalid.")
    #phone_number = models.CharField(validators=[phone_regex], max_length=15, default=None, blank=True, null=True)
    phone_number = models.CharField(max_length=15, unique=True)
    age = models.IntegerField(default=None, null=True, blank=True)
    address = models.TextField(default=None, blank=True, null=True)
    city = models.CharField(max_length=255,blank=True, null=True, default=None)
    zip_code = models.CharField(max_length=255, default=None, blank=True, null=True)
    current_location = models.ForeignKey(
        "UserLocation",
        related_name='users',
        default=None,
        null=True,
        blank=True,
        on_delete=models.SET_NULL)
    country = models.ForeignKey(
        "Country",
        related_name='users',
        default=None,
        null=True,
        blank=True,
        on_delete=models.SET_NULL)
    state = models.ForeignKey(
        "State",
        related_name='users',
        default=None,
        null=True,
        blank=True,
        on_delete=models.SET_NULL)
    title = models.TextField(default=None, blank=True, null=True)
    short_description = models.TextField(default='', blank=True, null=True)
    points = models.IntegerField(default=0)
    badges = models.ManyToManyField(
		"Badge",
        symmetrical=False,
		related_name='users')
    follows = models.ManyToManyField(
        'self',
        related_name='followers',
        symmetrical=False,
        default=None,
        blank=True)
    followers_count = models.IntegerField(default=0)
    favourite_dishes = models.ManyToManyField(
        'Dish',
        related_name='favourite_of',
        symmetrical=False,
        default=None,
        blank=True)
    liked_posts = models.ManyToManyField(
        'Post',
        related_name='liked_by',
        symmetrical=False,
        default=None,
        blank=True)
    liked_post_comments = models.ManyToManyField(
        'PostComment',
        related_name='liked_by',
        symmetrical=False,
        default=None,
        blank=True)

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []
    objects = UserManager()

    @property
    def username_(self):
        return self.id

    @property
    def profile_photos(self):
        return {
            'full_size': settings.DOMAIN_URL+self.photo.url,
            '400x400': settings.DOMAIN_URL+get_thumbnail(self.photo, '400x400', crop='center', quality=99).url,
            '200x200': settings.DOMAIN_URL+get_thumbnail(self.photo, '200x200', crop='center', quality=99).url,
            '100x100': settings.DOMAIN_URL+get_thumbnail(self.photo, '100x100', crop='center', quality=99).url,
            '50x50': settings.DOMAIN_URL+get_thumbnail(self.photo, '50x50', crop='center', quality=99).url,
            '30x30': settings.DOMAIN_URL+get_thumbnail(self.photo, '30x30', crop='center', quality=99).url,
        }

    @property
    def url(self):
        return "/ac/"+str(self.id)+"/"

    def get_absolute_url(self):
        return self.url

    def __str__(self):
        return str(self.id)

class OTP(AppModel):
    phone_regex = RegexValidator(regex=r'^[6789]\d{9}$', message="phone no. is invalid.")
    phone_number = models.CharField(validators=[phone_regex], max_length=10, unique=True)
    code = models.CharField(max_length=255)
    tries = models.IntegerField(default=0)

    def __str__(self):
        return str(self.phone_number) + ": "+str(self.code) + ": "+str(self.tries)

class Country(AppModel):
    title = models.CharField(max_length=255)
    iso_2 = models.CharField(max_length=2,blank=True, null=True, default=None)
    iso_3 = models.CharField(max_length=3,blank=True, null=True, default=None)
    phone_code = models.CharField(max_length=255,blank=True, null=True, default=None)
    capital = models.CharField(max_length=255,blank=True, null=True, default=None)
    currency = models.CharField(max_length=255,blank=True, null=True, default=None)
    flag = models.ImageField(upload_to='country_flags', blank=True, null=True, default=None)

    def __str__(self):
        return self.title

class Currency(AppModel):
    title = models.CharField(max_length=255,blank=True, null=True, default=None)
    code = models.CharField(max_length=255,unique=True)
    symbol = models.CharField(max_length=255,blank=True, null=True, default=None)

    def __str__(self):
        return str(self.title) + ": "+str(self.code)

class State(AppModel):
    country = models.ForeignKey(
        "Country",
        related_name='states',
        on_delete=models.CASCADE)
    title = models.CharField(max_length=255,blank=True, null=True, default=None)

    def __str__(self):
        return str(self.country)+ " : " + self.title

class City(AppModel):
    state = models.ForeignKey(
        "State",
        related_name='cities',
        on_delete=models.CASCADE)
    title = models.CharField(max_length=255,blank=True, null=True, default=None)

    def __str__(self):
        return str(self.state)+ " : " + self.title

class Location(AppModel):
    lat = models.CharField(max_length=255, default=None, blank=True, null=True)
    lng = models.CharField(max_length=255, default=None, blank=True, null=True)
    place_id = models.CharField(max_length=255, default=None, blank=True, null=True)
    address = models.TextField(default=None, blank=True, null=True)
    main_text = models.CharField(max_length=255, default=None, blank=True, null=True)
    secondary_text = models.CharField(max_length=255, default=None, blank=True, null=True)
    tag = models.CharField(max_length=255, default=None, blank=True, null=True)

class UserLocation(Location):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='locations',
        on_delete=models.CASCADE)
    is_saved = models.BooleanField(default=False)

    def __str__(self):
        return str(self.place_id)

class Badge(AppModel):
    name = models.CharField(max_length=255)
    short_description = models.TextField(default='', blank=True, null=True)
    description = models.TextField(default='', blank=True, null=True)


def get_provider_logo_upload_path(instance, filename):
    return os.path.join('images/providers/', timezone.localtime().date().strftime("%Y/%m/%d"), filename)

class Provider(AppModel):
    name = models.CharField(max_length=255)
    url = models.URLField()
    logo = ImageField(upload_to=get_provider_logo_upload_path,default=None, blank=True, null=True)
    background = models.CharField(max_length=1024, default='#fff', blank=True, null=True)

class PhoneNumber(AppModel):
    phone_number = models.CharField(max_length=255)

    class Meta:
        abstract = True

    def __str__(self):
        return self.phone_number

class RestaurantPhoneNumber(PhoneNumber):
    restaurant = models.ForeignKey(
        "Restaurant",
        related_name='phone_numbers',
        on_delete=models.CASCADE)

class RestaurantCategory(AppModel):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

class RestaurantFeature(AppModel):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

class RestaurantCollection(AppModel):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

class RestaurantCuisine(AppModel):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

class PaymentMode(AppModel):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name

class Restaurant(AppModel):
    ref_id = models.CharField(max_length=255, default=None, blank=True, null=True)
    zomato_link = models.URLField(default=None, blank=True, null=True)
    name = models.CharField(max_length=1024)
    description = models.TextField(default=None, blank=True, null=True)
    logo = ImageField(upload_to=get_photo_upload_path,default=None, null=True, blank=True)
    lat = models.CharField(max_length=255, default=None, blank=True, null=True)
    lng = models.CharField(max_length=255, default=None, blank=True, null=True)
    lat_lng = models.PointField(null=True, blank=True, srid=4326)
    address = models.TextField(default=None, blank=True, null=True)
    location = models.CharField(max_length=1024, default=None, blank=True, null=True)
    zomato_rating = models.DecimalField(max_digits=3,decimal_places=1,default=None, blank=True, null=True)
    rating = models.DecimalField(max_digits=3,decimal_places=1,default=None, blank=True, null=True)
    delivery_rating = models.DecimalField(max_digits=3,decimal_places=1,default=None, blank=True, null=True)
    delivery_cost = models.DecimalField(max_digits=10,decimal_places=2,default=None, blank=True, null=True)
    cost_for_two = models.IntegerField(default=None, blank=True, null=True)
    categories = models.ManyToManyField(
		"RestaurantCategory",
        symmetrical=False,
        default=None,
        blank=True,
		related_name='restaurants')
    cuisines = models.ManyToManyField(
		"RestaurantCuisine",
        symmetrical=False,
        default=None,
        blank=True,
		related_name='restaurants')
    features = models.ManyToManyField(
		"RestaurantFeature",
        symmetrical=False,
        default=None,
        blank=True,
		related_name='restaurants')
    collections = models.ManyToManyField(
		"RestaurantCollection",
        symmetrical=False,
        default=None,
        blank=True,
		related_name='restaurants')
    payment_modes = models.ManyToManyField(
		"PaymentMode",
        symmetrical=False,
        default=None,
        blank=True,
		related_name='restaurants')
    tags = models.ManyToManyField(
		"Tag",
        symmetrical=False,
        default=None,
        blank=True,
		related_name='restaurants')
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='restaurants',
        default=None,
        null=True,
        blank=True,
        on_delete=models.SET_NULL)

    @property
    def resized_logos(self):
        return {
            'full_size': settings.DOMAIN_URL+self.logo.url,
            '200x200': settings.DOMAIN_URL+get_thumbnail(self.logo, '200x200', crop='center', quality=99).url,
            '100x100': settings.DOMAIN_URL+get_thumbnail(self.logo, '100x100', crop='center', quality=99).url,
            '50x50': settings.DOMAIN_URL+get_thumbnail(self.logo, '50x50', crop='center', quality=99).url,
            '30x30': settings.DOMAIN_URL+get_thumbnail(self.logo, '30x30', crop='center', quality=99).url,
        } if self.logo else ""

    def __str__(self):
        return self.name

class RestaurantRatingType(AppModel):
    name = models.CharField(max_length=255)

class RestaurantRating(AppModel):
    restaurant = models.ForeignKey(
        "Restaurant",
        related_name='ratings',
        on_delete=models.CASCADE)
    rating_type = models.ForeignKey(
        "RestaurantRatingType",
        related_name='ratings',
        on_delete=models.CASCADE)
    stars = models.IntegerField()

class DishTag(AppModel):
    name = models.CharField(max_length=255)
    photo = ImageField(upload_to=get_photo_upload_path,default=None, null=True, blank=True)

    @property
    def resized_photos(self):
        return {
            'full_size': settings.DOMAIN_URL+self.photo.url,
            '200x200': settings.DOMAIN_URL+get_thumbnail(self.photo, '200x200', crop='center', quality=99).url,
            '100x100': settings.DOMAIN_URL+get_thumbnail(self.photo, '100x100', crop='center', quality=99).url,
            '50x50': settings.DOMAIN_URL+get_thumbnail(self.photo, '50x50', crop='center', quality=99).url,
            '30x30': settings.DOMAIN_URL+get_thumbnail(self.photo, '30x30', crop='center', quality=99).url,
        } if self.photo else None

    def __str__(self):
        return self.name

class Dish(AppModel):
    VEG = 'V'
    NON_VEG = 'NV'
    DIET_TYPES = (
        (VEG, 'Veg'),
        (NON_VEG, 'Non Veg')
    )
    restaurant = models.ForeignKey(
        "Restaurant",
        related_name = 'dishes',
        on_delete = models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(default='', blank=True, null=True)
    diet = models.CharField(max_length=2, default=None, blank=True, null=True, choices=DIET_TYPES)
    zomato_rating = models.DecimalField(max_digits=2,decimal_places=1,default=None, blank=True, null=True)
    zomato_number_of_ratings = models.IntegerField(default=None, blank=True, null=True)
    rating = models.DecimalField(max_digits=2,decimal_places=1,default=None, blank=True, null=True)
    no_of_ratings = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=15,decimal_places=2,default=None, blank=True, null=True)
    score = models.DecimalField(max_digits=15,decimal_places=5,default=0)
    tags = models.ManyToManyField(
		"DishTag",
        symmetrical=False,
        default=None,
        blank=True,
		related_name='dishes')
    photo = ImageField(upload_to=get_photo_upload_path,default=None, null=True, blank=True)

    @property
    def resized_photos(self):
        return {
            'full_size': settings.DOMAIN_URL+self.photo.url,
            '200x200': settings.DOMAIN_URL+get_thumbnail(self.photo, '300x300', crop='center', quality=99).url,
            '200x200': settings.DOMAIN_URL+get_thumbnail(self.photo, '200x200', crop='center', quality=99).url,
            '100x100': settings.DOMAIN_URL+get_thumbnail(self.photo, '100x100', crop='center', quality=99).url,
            '50x50': settings.DOMAIN_URL+get_thumbnail(self.photo, '50x50', crop='center', quality=99).url,
            '30x30': settings.DOMAIN_URL+get_thumbnail(self.photo, '30x30', crop='center', quality=99).url,
        } if self.photo else ""

    @property
    def files_(self):
        arr = []
        for file in self.files.all()[:5]:
            if file.file_:
                arr.append(file.file_)
        return arr

    def __str__(self):
        return self.restaurant.name+" : "+self.name

class File(AppModel):
    file = models.FileField(upload_to=get_file_upload_path)
    type = models.CharField(max_length=255, default=None, blank=True, null=True)
    order = models.IntegerField(default=0)

    class Meta:
        abstract = True

    @property
    def file_(self):
        print(self.type)
        if self.type.lower() in settings.PHOTO_FILE_EXTENSIONS:
            return {
                "id": self.id,
                "type": "image",
                "full_size": settings.DOMAIN_URL+get_thumbnail(self.file, "400x400", crop='noop', quality=99).url,
                "resized": settings.DOMAIN_URL+get_thumbnail(self.file, settings.PHOTO_SIZE, crop='noop', quality=99).url
            }
        return None

    def __str__(self):
        return "{} {}".format(self.id, self.type)

class RestaurantFile(File):
    restaurant = models.ForeignKey(
        "Restaurant",
        related_name='files',
        on_delete=models.CASCADE)

class DishFile(File):
    dish = models.ForeignKey(
        "Dish",
        related_name='files',
        on_delete=models.CASCADE)

    def __str__(self):
        return str(self.id)

class DishRatingType(AppModel):
    name = models.CharField(max_length=255)

class DishRating(AppModel):
    dish = models.ForeignKey(
        "Dish",
        related_name='ratings',
        on_delete=models.CASCADE)
    rating_type = models.ForeignKey(
        "DishRatingType",
        related_name='ratings',
        on_delete=models.CASCADE)
    stars = models.IntegerField()

class Tag(AppModel):
    name = models.CharField(max_length=100, unique=True)
    short_description = models.TextField(default='', blank=True, null=True)
    description = models.TextField(default='', blank=True, null=True)
    photo = ImageField(upload_to=get_photo_upload_path,default=None, null=True, blank=True)

    @property
    def resized_photos(self):
        return {
            'full_size': settings.DOMAIN_URL+self.photo.url,
            '200x200': settings.DOMAIN_URL+get_thumbnail(self.photo, '200x200', crop='center', quality=99).url,
            '100x100': settings.DOMAIN_URL+get_thumbnail(self.photo, '100x100', crop='center', quality=99).url,
            '50x50': settings.DOMAIN_URL+get_thumbnail(self.photo, '50x50', crop='center', quality=99).url,
            '30x30': settings.DOMAIN_URL+get_thumbnail(self.photo, '30x30', crop='center', quality=99).url,
        } if self.photo else ""

    def __str__(self):
        return self.name


class DishCollection(AppModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='dish_collections',
        on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    photo = ImageField(upload_to=get_file_upload_path, default=None, blank=True, null=True)
    description = models.TextField(default=None, blank=True, null=True)
    dishes = models.ManyToManyField(
		"Dish",
        symmetrical=False,
        default=None,
        blank=True,
		related_name='dish_collections')

    @property
    def resized_photos(self):
        return {
            'full_size': settings.DOMAIN_URL+self.photo.url,
            '200x200': settings.DOMAIN_URL+get_thumbnail(self.photo, '200x200', crop='center', quality=99).url,
            '100x100': settings.DOMAIN_URL+get_thumbnail(self.photo, '100x100', crop='center', quality=99).url,
            '50x50': settings.DOMAIN_URL+get_thumbnail(self.photo, '50x50', crop='center', quality=99).url,
            '30x30': settings.DOMAIN_URL+get_thumbnail(self.photo, '30x30', crop='center', quality=99).url,
        } if self.photo else ""

    def __str__(self):
        return "{0} : {1}".format(self.id, self.user.id)

class Post(AppModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='posts',
        on_delete=models.CASCADE)
    restaurant = models.ForeignKey(
        "Restaurant",
        related_name='posts',
        default=None,
        null=True,
        blank=True,
        on_delete=models.CASCADE)
    dish = models.ForeignKey(
        "Dish",
        related_name='posts',
        default=None,
        null=True,
        blank=True,
        on_delete=models.CASCADE)
    other_restaurant = models.CharField(max_length=255, default=None, blank=True, null=True)
    other_dish = models.CharField(max_length=255, default=None, blank=True, null=True)
    description = models.TextField(default='', blank=True, null=True)
    rating = custom_fields.IntegerRangeField(min_value=1, max_value=5)
    tags = models.ManyToManyField(
		"Tag",
        symmetrical=False,
        default=None,
        blank=True,
		related_name='posts')
    showcase_comment = models.ForeignKey(
        "PostComment",
        related_name='posts',
        default=None,
        null=True,
        blank=True,
        on_delete=models.CASCADE)
    upvotes_count = models.IntegerField(default=0)
    downvotes_count = models.IntegerField(default=0)
    user_lat = models.CharField(max_length=255, default=None, blank=True, null=True)
    user_lng = models.CharField(max_length=255, default=None, blank=True, null=True)

    @property
    def files_(self):
        arr = []
        for file in self.post_files.all():
            if file.file_:
                arr.append(file.file_)
        return arr

    @property
    def comments_count(self):
        return self.comments.all().count()

    @property
    def likes_count(self):
        return self.liked_by.all().count()

    @property
    def url(self):
        return ""

    def __str__(self):
        return str(self.id)


class PostFile(File):
    post = models.ForeignKey(
        'Post',
        related_name='post_files',
        on_delete=models.CASCADE)

class PostComment(AppModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='comments',
        on_delete=models.CASCADE)
    post = models.ForeignKey(
        "Post",
        related_name='comments',
        on_delete=models.CASCADE)
    parent = models.ForeignKey(
        'self',
        related_name='comments',
        default=None,
        null=True,
        blank=True,
        on_delete=models.CASCADE)
    description =  models.TextField(default='', blank=True, null=True)
    upvotes_count = models.IntegerField(default=0)

    @property
    def likes_count(self):
        return self.liked_by.all().count()

    @property
    def url(self):
        return ""

    def __str__(self):
        return str(self.id)

class Activity(AppModel):
    BOOKMARK = 'B'
    RECOMMEND = 'R'
    UP_VOTE = 'U'
    DOWN_VOTE = 'D'
    ACTIVITY_TYPES = (
        (BOOKMARK, 'Bookmark'),
        (RECOMMEND, 'Recommend'),
        (UP_VOTE, 'Up Vote'),
        (DOWN_VOTE, 'Down Vote'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        # related_name='activities',
        on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=1,  blank=False, choices=ACTIVITY_TYPES)

    # Below the mandatory fields for generic relation
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()

    def __str__(self):
        return self.content_type.model+" : "+str(self.object_id)

class TokenBlackList(AppModel):
    token = models.TextField()

class NearbyStore(AppModel):
    dishes = models.ManyToManyField(
		"Dish",
        symmetrical=False,
		related_name='nearby_stores')

class Feedback(AppModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="feedbacks",
        on_delete=models.CASCADE)
    rating = custom_fields.IntegerRangeField(min_value=1, max_value=5)
    description = models.TextField()

    def __str__(self):
        return  str(self.user.phone_number)

class DataStore(AppModel):
    # max_zomato_number_of_ratings = models.DecimalField(max_digits=15,decimal_places=5, default=0)
    new_dish_rating = models.DecimalField(max_digits=5,decimal_places=2, default=0)
    weightage_distance = models.IntegerField(default=0)
    weightage_zomato_rating = models.IntegerField(default=0)
    weightage_zomato_number_of_ratings = models.IntegerField(default=0)
    zomato_number_of_ratings_threshold = models.DecimalField(max_digits=4, decimal_places=2, default=0)
    weightage_tofu_rating = models.IntegerField(default=0)
    weightage_tofu_number_of_ratings = models.IntegerField(default=0)
    weightage_files = models.IntegerField(default=0)
