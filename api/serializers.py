from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
import os, math, random, re, json
phone_number_regex = re.compile("^[6789]\d{9}$")
from django.utils.translation import ugettext_lazy as _
from django.db import transaction
from django.db.transaction import on_commit
from django.urls import reverse_lazy
from decimal import *
from app.models import *
from app.choices import *
from app.tokens import random_string_generator
from app.tasks import task_send_activation_mail, task_send_confirmation_mail
from api.custom_fields import Base64ImageField
from app.settings import PHONE_REGEX, PASSWORD_MIN_LENGTH, OTP_LENGTH, OTP_TRIES, OTP_EXPIRY
from django.conf import settings
from django.utils import timezone
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
import json
from django.http import HttpResponse
from wsgiref.util import FileWrapper
from django.core.files.uploadedfile import InMemoryUploadedFile
import zipfile
from io import StringIO
from api.utils import is_json
from app.utils import generate_otp, get_secret_key, generate_code, generate_campaign_task_batch_code
import app.choices as choices
from django.conf import settings
import googlemaps
from .background_tasks import task_send_otp_sms
gmaps = googlemaps.Client(key=settings.GOOGLE_API_KEY)

username_regex=re.compile('^[a-z0-9_.]+$')

def is_otp_valid(phone_number, code):
    instance = None
    pq = OTP.objects.filter(phone_number=phone_number)
    if pq.exists():
        instance = pq[0]
        if instance.code == code:
            instance.delete()
            return True
        instance.tries += 1
        if instance.tries >= OTP_TRIES:
            instance.delete()
        else:
            instance.save()
    return False

class OTPSerializer(serializers.ModelSerializer):
    INTENTS = ["signup", "change password"]
    phone_number = serializers.RegexField(PHONE_REGEX, max_length=10, min_length=10)
    intent = serializers.ChoiceField(choices=INTENTS, required = False)

    class Meta:
        model = OTP
        fields = ('id', 'phone_number', 'intent')

    def create(self, validated_data):
        phone_number = validated_data["phone_number"]
        intent = validated_data.pop("intent", None)
        if intent and intent == "signup" and User.objects.filter(phone_number=phone_number).exists():
            raise serializers.ValidationError("User with this phone number already exists")
        validated_data["code"] = generate_otp()
        validated_data["tries"] = 0
        q = OTP.objects.filter(phone_number=phone_number)
        instance = None
        if q.exists():
            instance = q[0]
            instance.code = validated_data["code"]
            instance.tries = validated_data["tries"]
            instance.save()
        else:
            instance = super().create(validated_data)
        task_send_otp_sms.delay(instance.phone_number, instance.code)
        instance.code = instance.code[0] + ('*'*OTP_LENGTH)
        return instance

class OTPCREATESerializer(OTPSerializer):
    code = serializers.CharField(read_only=True, required=False)
    class Meta(OTPSerializer.Meta):
        model = OTP
        fields = OTPSerializer.Meta.fields+('code',)
        read_only_fields = ('code',)

class PasswordResetSerializer(serializers.Serializer):
    otp = serializers.CharField(max_length=None, required=True, error_messages={"required": "OTP is required"})
    password = serializers.CharField(max_length=None, required=True,  error_messages={"required": "Password is required"})
    phone_number = serializers.CharField(max_length=None, required=True, error_messages={"required": "Phone Number is required"})


    def validate_otp(self, value):
        if len(value) != OTP_LENGTH :
            raise serializers.ValidationError("OTP is invalid.")
        return value

    def validate_phone_number(self, value):
        pattern = re.compile("^([6789]\d{9})$")
        if not pattern.match(value):
            raise serializers.ValidationError("Phone Number is invalid.")
        if not User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("Phone Number is not registered yet.")
        return value

    def validate_password(self, value):
        if len(value)<PASSWORD_MIN_LENGTH :
            raise serializers.ValidationError("password must contain atleast 8 characters..")
        return value

    def validate(self, attrs):
        otp = attrs["otp"]
        phone_number = attrs["phone_number"]
        is_otp_valid(phone_number, otp)
        return attrs


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ('id', 'title',)

class CountryDETAILSerializer(CountrySerializer):
    pass

class CountryCREATESerializer(CountrySerializer):
    pass

class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ('id', 'country', 'title',)

class StateDETAILSerializer(CountrySerializer):
    country = CountrySerializer()

class StateCREATESerializer(CountrySerializer):
    pass

class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = City
        fields = ('id', 'state', 'title',)

class CityDETAILSerializer(CountrySerializer):
    state = StateDETAILSerializer()

class CityCREATESerializer(CountrySerializer):
    pass

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ('id', 'place_id', 'address', 'main_text', 'secondary_text',
            'lat', 'lng', 'tag', 'date_created')


class UserLocationSerializer(LocationSerializer):
    class Meta(LocationSerializer.Meta):
        model = UserLocation
        fields = LocationSerializer.Meta.fields+('user', 'is_saved')

class UserLocationDETAILSerializer(UserLocationSerializer):
    pass

class UserLocationLISTSerializer(UserLocationSerializer):
    pass

class UserLocationCREATESerializer(UserLocationSerializer):
    place_id = serializers.CharField(required=True)

    class Meta(UserLocationSerializer.Meta):
        read_only_fields = ('user', )

    def create(self, validated_data):
        validated_data["user"] = self.context["user"]
        q = UserLocation.objects.filter(place_id=validated_data["place_id"], user=validated_data["user"])
        if q.exists():
            instance = q[0]
        else:
            res = gmaps.reverse_geocode(validated_data["place_id"])
            validated_data["address"] = res[0]["formatted_address"]
            validated_data["lat"] = res[0]["geometry"]["location"]["lat"]
            validated_data["lng"] = res[0]["geometry"]["location"]["lng"]
            instance = super().create(validated_data)
        return instance

class UserLocationUPDATESerializer(UserLocationSerializer):
    pass

class UserLocationPATCHSerializer(UserLocationSerializer):
    pass

class UserLocationDELETESerializer(UserLocationSerializer):
    pass

class UserSerializer(serializers.ModelSerializer):
    followed_by_you = serializers.SerializerMethodField()
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    posts_count = serializers.SerializerMethodField()
    reputation = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ('id', 'username', 'phone_number', 'name', 'title',
            'short_description', 'current_location',
            'gender', 'photo', 'profile_photos', 'age',
            'address', 'zip_code', 'city', 'country',
            'state', 'posts_count', 'reputation', 'followers_count',
            'following_count', 'followed_by_you', 'url', 'date_created')
        extra_kwargs = {
            'username': {"error_messages":{
                "required": "username is required",
                "blank": "username is required",
                "invalid": "username is invalid",
                }
            },
            'phone_number': {"error_messages":{
                "required": "phone number is required",
                "blank": "phone number is required",
                "invalid": "phone number is invalid",
                }
            },
            'password': {"error_messages":{
                "required": "password is required",
                "blank": "password is required",
                "invalid": "password is invalid",
                }
            },
        }

    def get_followed_by_you(self, obj):
        user = self.context.get("user", None)
        if user:
            return obj in self.context["user"].follows.all()
        return False

    def get_reputation(self, obj):
        followers_count = obj.followers.all().count()
        follows_count = obj.follows.all().count()
        posts_count = obj.posts.all().count()
        result = 2*followers_count - follows_count + 5*posts_count
        if result <= 0:
            return 0
        return math.ceil(result/10)

    def get_posts_count(self, obj):
        return obj.posts.all().count()

    def get_followers_count(self, obj):
        return obj.followers.all().count()

    def get_following_count(self, obj):
        return obj.follows.all().count()

class UserLISTSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        fields = ('id', 'username', 'name', 'title',
            'short_description', 'current_location',
            'gender', 'photo', 'profile_photos', 'age',
            'address', 'zip_code', 'city', 'country',
            'state', 'posts_count', 'reputation', 'followers_count',
            'following_count', 'followed_by_you', 'url', 'date_created')
        read_only_fields = ('password',)

class UserDETAILSerializer(UserLISTSerializer):
    country = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    class Meta(UserSerializer.Meta):
        pass

    def get_country(self, obj):
        if obj.country:
            return obj.country.title
        return ""

    def get_state(self, obj):
        if obj.state:
            return obj.state.title
        return ""

class UserCREATESerializer(UserSerializer):
    otp = serializers.CharField()
    skip_password = False

    def __init__(self, skip_password=False, *args, **kwargs):
        super(UserCREATESerializer, self).__init__(*args, **kwargs)
        self.skip_password=skip_password;
        if self.skip_password:
            self.fields['password'] = serializers.CharField(required=False)

    def to_representation(self, instance):
        serializer = AuthUserSerializer(instance=instance)
        return serializer.data

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields+('password', 'otp' )
        read_only_fields = ('follows', )

    def validate_password(self, value):
        if self.skip_password:
            return get_secret_key()
        if not self.skip_password and len(value)<PASSWORD_MIN_LENGTH :
            raise serializers.ValidationError("password must contain atleast 8 characters..")
        return value

    def validate_username(self, username):
        username = username.replace(" ", "").lower()
        if not username_regex.match(username):
            raise serializers.ValidationError("Username is invalid.")
        return username

    def validate(self, attrs):
        phone_number = attrs["phone_number"]
        otp = attrs.pop("otp", "")
        if not is_otp_valid(phone_number, otp):
            raise serializers.ValidationError("OTP is invalid")
        username = attrs["username"]
        name = attrs.get("name", None)
        if not name:
            attrs["name"] = username
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create(**validated_data)
        if self.skip_password:
            validated_data["password"] = get_secret_key()
        user.set_password(validated_data['password'])
        user.is_active=True
        user.save()
        user.otp = "";
        return user


class UserUPDATESerializer(UserSerializer):
    is_authenticated = serializers.BooleanField(default=True, read_only=True)
    photo = Base64ImageField(
        max_length=None, use_url=True, required=False
    )

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ('is_authenticated',)
        read_only_fields = ('id', 'phone_number', 'is_authenticated')

    def to_representation(self, instance):
        serializer = UserDETAILSerializer(instance=instance)
        return serializer.data

    @transaction.atomic
    def update(self, instance, validated_data):
        instance.__dict__.update(**validated_data)
        instance.save()
        instance = super().update(instance, validated_data)
        return instance

class AuthUserSerializer(UserDETAILSerializer):
    is_authenticated = serializers.BooleanField(default=False)
    current_location = serializers.SerializerMethodField()
    current_location = UserLocationSerializer()

    class Meta(UserSerializer.Meta):
        model = User
        fields = UserSerializer.Meta.fields+('is_authenticated',)

    def get_current_location(self, obj):
        if obj.current_location:
            return UserLocationSerializer(instance=obj.current_location)
        return {
                "place_id": "ChIJLbZ-NFv9DDkRzk0gTkm3wlI",
                "address": "New Delhi, Delhi, India",
                "main_text": null,
                "secondary_text": null,
                "lat": "28.6139391",
                "lng": "77.2090212",
            }


class AuthUserPOSTSerializer(serializers.ModelSerializer):
    password = serializers.CharField(required=False, write_only=True)
    class Meta:
        model = User
        fields = ('id', 'username', 'name', 'password', 'photo', 'title',
            'short_description', 'address', 'current_location')

    def validate_username(self, username):
        username = username.replace(" ", "").lower()
        if not username_regex.match(username):
            raise serializers.ValidationError("Username is invalid.")
        return username

    def to_representation(self, instance):
        serializer = AuthUserSerializer(instance=instance)
        return serializer.data

class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = ('id', 'name', 'short_description', 'description', 'date_created')

class FollowSerializer(serializers.Serializer):
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=True)
    class Meta:
        fields = ('user', 'followers_count',)

    def validate_user(self, user):
        if user==self.context["user"]:
            raise serializers.ValidationError("You can't follow you.")
        return user

    def create(self, validated_data):
        auth_user = self.context["user"]
        user = validated_data["user"]
        status = False
        if user in auth_user.follows.all():
            auth_user.follows.remove(user)
            status = False
        else:
            auth_user.follows.add(user)
            status = True
        return {"status": status}

class FavouriteDishSerializer(serializers.Serializer):
    dish = serializers.PrimaryKeyRelatedField(queryset=Dish.objects.all(), required=True)
    class Meta:
        fields = ('dish',)

    def create(self, validated_data):
        user = self.context["user"]
        dish = validated_data["dish"]
        status = False
        if dish in user.favourite_dishes.all():
            user.favourite_dishes.remove(dish)
            status = False
        else:
            user.favourite_dishes.add(dish)
            status = True
        return {"status": status}

class LikePostSerializer(serializers.Serializer):
    post = serializers.PrimaryKeyRelatedField(queryset=Post.objects.all(), required=True)
    class Meta:
        fields = ('post', )

    def create(self, validated_data):
        user = self.context["user"]
        post = validated_data["post"]
        status = False
        if post in user.liked_posts.all():
            user.liked_posts.remove(post)
            status = False
        else:
            user.liked_posts.add(post)
            status = True
        return {"status": status, "likes_count": post.likes_count}

class LikePostCommentSerializer(serializers.Serializer):
    comment = serializers.PrimaryKeyRelatedField(queryset=PostComment.objects.all(), required=True)
    class Meta:
        fields = ('comment', )

    def create(self, validated_data):
        user = self.context["user"]
        comment = validated_data["comment"]
        status = False
        if comment in user.liked_post_comments.all():
            user.liked_post_comments.remove(comment)
            status = False
        else:
            user.liked_post_comments.add(comment)
            status = True
        return {"status": status, "likes_count": comment.likes_count}

class ProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provider
        fields = ('id', 'name', 'url', 'logo', 'background', 'date_created')

class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = ('id', 'file', 'type', 'file_', 'order', 'date_created')

class RestaurantFileSerializer(FileSerializer):
    class Meta(FileSerializer.Meta):
        model = RestaurantFile
        fields = FileSerializer.Meta.fields+('restaurant',)

class DishFileSerializer(FileSerializer):
    class Meta(FileSerializer.Meta):
        model = DishFile
        fields = FileSerializer.Meta.fields+('dish',)

class PostFileSerializer(FileSerializer):
    class Meta(FileSerializer.Meta):
        model = PostFile
        fields = FileSerializer.Meta.fields+('post',)

class PostFileDETAILSerializer(PostFileSerializer):
    pass

class PostFileLISTSerializer(PostFileSerializer):
    pass

class PostFileCREATESerializer(PostFileSerializer):
    pass

class PostFileUPDATESerializer(PostFileSerializer):
    pass

class PostFilePATCHSerializer(PostFileSerializer):
    pass

class PostFileDELETESerializer(PostFileSerializer):
    pass

class RestaurantPhoneNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantPhoneNumber
        fields = ('id', 'phone_number', 'restaurant', 'date_created')

class RestaurantCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantCategory
        fields = ('id', 'name', 'date_created')

class RestaurantFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantFeature
        fields = ('id', 'name', 'date_created')

class RestaurantCollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantCollection
        fields = ('id', 'name', 'date_created')

class RestaurantCuisineSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantCuisine
        fields = ('id', 'name', 'date_created')

class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ('id', 'ref_id', 'zomato_link', 'name', 'description', 'logo',
            'lat', 'lng', 'address', 'location', 'zomato_rating', 'rating',
            'delivery_rating', 'delivery_cost', 'cost_for_two', 'payment_modes',
            'categories', 'cuisines', 'features', 'collections', 'payment_modes',
            'tags', 'admin', 'date_created')


class RestaurantLISTSerializer(RestaurantSerializer):
    cuisines = serializers.SerializerMethodField()

    def get_cuisines(self, obj):
        return [cuisine.name for cuisine in obj.cuisines.all()]

class RestaurantDETAILSerializer(RestaurantLISTSerializer):
    pass

class RestaurantCREATESerializer(RestaurantSerializer):
    pass

class RestaurantUPDATESerializer(RestaurantSerializer):
    pass

class RestaurantPATCHSerializer(RestaurantSerializer):
    pass

class RestaurantDELETESerializer(RestaurantSerializer):
    pass

class RestaurantRatingTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantRatingType
        fields = ('id', 'name', 'date_created')

class RestaurantRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantRating
        fields = ('id', 'restaurant', 'rating_type', 'stars', 'date_created')

class DishTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = DishTag
        fields = ('id', 'name', 'date_created')

class DishTagDETAILSerializer(DishTagSerializer):
    pass

class DishTagLISTSerializer(DishTagSerializer):
    pass

class DishTagCREATESerializer(DishTagSerializer):

    def validate_name(self, name):
        if DishTag.objects.filter(name=name).exists():
            raise serializers.ValidationError("Dish Type "+name+" already exists.")
        return name

class DishTagUPDATESerializer(DishTagSerializer):
    pass

class DishTagPATCHSerializer(DishTagSerializer):
    pass

class DishTagDELETESerializer(DishTagSerializer):
    pass

class DishSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dish
        fields = ('id', 'restaurant', 'name', 'description', 'diet',
            'rating', 'price', 'files_', 'files', 'tags', 'score', 'date_created')

class DishLISTSerializer(DishSerializer):
    # files = DishFileSerializer(many=True)
    restaurant__name = serializers.CharField(source="restaurant.name")
    restaurant__location = serializers.CharField(source="restaurant.location")
    restaurant__lat = serializers.CharField(source="restaurant.lat")
    restaurant__lng = serializers.CharField(source="restaurant.lng")
    distance = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    total_no_of_reviews = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    is_favourite = serializers.SerializerMethodField()

    class Meta(DishSerializer.Meta):
        fields = DishSerializer.Meta.fields+('restaurant__name',
            'restaurant__location', 'restaurant__lat', 'restaurant__lng',
            'distance', 'total_no_of_reviews', 'is_favourite')

    def get_distance(self, obj):
        if hasattr(obj, "distance"):
            return obj.distance.m
        return None

    def get_rating(self, obj):
        if obj.rating:
            return obj.rating
        return obj.zomato_rating

    def get_total_no_of_reviews(self, obj):
        posts_count = obj.posts.count()
        if posts_count>0:
            return posts_count
        return None

    def get_tags(self, obj):
        return [tag.name for tag in obj.tags.all()]

    def get_is_favourite(self, obj):
        return obj in self.context["user"].favourite_dishes.all()

class DishDETAILSerializer(DishLISTSerializer):
    pass

class _FileSerializer(serializers.Serializer):
    file = serializers.FileField(max_length=None, allow_empty_file=False)

class DishCREATESerializer(DishSerializer):
    files = serializers.ListField(required=False)

    def to_representation(self, instance):
        serializer = DishLISTSerializer(instance=instance, context=self.context)
        return serializer.data


class DishUPDATESerializer(DishSerializer):
    pass

class DishPATCHSerializer(DishSerializer):
    pass

class DishDELETESerializer(DishSerializer):
    pass


class DishRatingTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DishRatingType
        fields = ('id', 'name', 'date_created')

class DishRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = DishRating
        fields = ('id', 'dish', 'rating_type', 'stars', 'date_created')

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'short_description', 'description', 'photo',
                'resized_photos', 'date_created')

class DishCollectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DishCollection
        fields = ('id', 'user', 'photo', 'dishes', 'name', 'description', 'date_created')

class DishCollectionLISTSerializer(DishCollectionSerializer):
    pass

class DishCollectionDETAILSerializer(DishCollectionLISTSerializer):
    pass

class DishCollectionCREATESerializer(DishCollectionSerializer):
    class Meta(DishCollectionSerializer.Meta):
        read_only_fields = ('user',)

    def validate(self, attrs):
        attrs["user"] = self.context["user"]
        return attrs

class DishCollectionUPDATESerializer(DishCollectionLISTSerializer):
    pass

class DishCollectionPATCHSerializer(DishCollectionLISTSerializer):
    pass

class PostCommentSerializer(serializers.ModelSerializer):
    is_liked = serializers.SerializerMethodField()
    class Meta:
        model = PostComment
        fields = ('id', 'user', 'post', 'parent', 'description',
            'is_liked', 'likes_count', 'date_created')
        read_only_fields = ('user', )

    def get_is_liked(self, obj):
        user = self.context.get("user", None)
        if not user:
            return False
        return user.liked_post_comments.filter(pk=obj.pk).exists()

class PostCommentLISTSerializer(PostCommentSerializer):
    user__id = serializers.CharField(source="user.id")
    user__username = serializers.CharField(source="user.username")
    user__profile_photos = serializers.JSONField(source="user.profile_photos")

    class Meta(PostCommentSerializer.Meta):
        fields = PostCommentSerializer.Meta.fields+('user__id', 'user__username', 'user__profile_photos',)

class PostCommentDETAILSerializer(PostCommentLISTSerializer):
    pass

class PostCommentCREATESerializer(PostCommentSerializer):
    class Meta(PostCommentSerializer.Meta):
        read_only_fields = PostCommentSerializer.Meta.read_only_fields+('upvotes_count',)

    def to_representation(self, instance):
        serializer = PostCommentDETAILSerializer(instance=instance, context=self.context)
        return serializer.data

    def validate(self, attrs):
        attrs["user"] = self.context["user"]
        return attrs

class PostCommentUPDATESerializer(PostCommentSerializer):
    pass

class PostCommentPATCHSerializer(PostCommentSerializer):
    pass

class PostCommentDELETESerializer(PostCommentSerializer):
    pass


class PostCommentActivitySerializer(serializers.ModelSerializer):
    post_comment_content_type = ContentType.objects.get_for_model(PostComment)
    post_comment = serializers.PrimaryKeyRelatedField(source="object_id", queryset=PostComment.objects.all())
    class Meta:
        model = Activity
        fields = ('id', 'user', 'activity_type', 'post_comment', 'date_modified')
        read_only_fields = ("user", "content_type")

class PostCommentActivityDETAILSerializer(PostCommentActivitySerializer):
    pass

class PostCommentActivityLISTSerializer(PostCommentActivitySerializer):
    pass

class PostCommentActivityCREATESerializer(PostCommentActivitySerializer):
    UP_VOTE_DOWN_VOTE = [Activity.UP_VOTE, Activity.DOWN_VOTE]
    post_comment = serializers.PrimaryKeyRelatedField(queryset=PostComment.objects.all())
    activity_type = serializers.CharField(required=True)

    def to_representation(self, instance):
        serializer = PostCommentActivityDETAILSerializer(instance=instance, context=self.context)
        return serializer.data

    def validate_activity_type(self, activity_type):
        if not activity_type in [Activity.UP_VOTE, Activity.DOWN_VOTE]:
            raise serializers.ValidationError("Unknow Activity")
        return activity_type

    def validate_post_comment(self, post_comment):
        # activity_type = self.initial_data["activity_type"]
        # if post_comment.user==self.context["user"] and activity_type in self.UP_VOTE_DOWN_VOTE:
        #     raise serializers.ValidationError("Oh! You cannot upvote/downvote your own comment")
        return post_comment

    def validate(self, attrs):
        attrs["user"] = self.context["user"]
        attrs["content_type"] = self.post_comment_content_type
        return attrs

    def create(self, validated_data):
        user = validated_data["user"]
        post_comment = validated_data.pop("post_comment")
        validated_data["object_id"] = post_comment.id
        activity_type = validated_data["activity_type"]
        paq = None
        if activity_type in self.UP_VOTE_DOWN_VOTE:
            paq = Activity.objects.filter(user=user, content_type=self.post_comment_content_type, object_id=post_comment.id, activity_type__in=self.UP_VOTE_DOWN_VOTE)
        else:
            paq = Activity.objects.filter(user=user, content_type=self.post_comment_content_type, object_id=post_comment.id, activity_type=activity_type)
        if not paq.exists():
            instance = Activity.objects.create(**validated_data)
        else:
            instance = paq[0]
            if activity_type == instance.activity_type:
                instance.delete()
            else:
                instance.activity_type=activity_type
                instance.save()
        return instance

class PostCommentActivityPUTSerializer(PostCommentActivitySerializer):
    pass

class PostCommentActivityPATCHSerializer(PostCommentActivitySerializer):
    pass

class PostCommentActivityDELETESerializer(PostCommentActivitySerializer):
    pass

class PostSerializer(serializers.ModelSerializer):
    post_content_type = ContentType.objects.get_for_model(Post)
    upvoted = serializers.SerializerMethodField()
    bookmarked = serializers.SerializerMethodField()
    class Meta:
        model = Post
        fields = ('id', 'user', 'files_', 'restaurant', 'dish', 'other_restaurant', 'other_dish',
            'description', 'rating', 'tags', 'showcase_comment', 'comments_count',
            'bookmarked', 'likes_count', 'user_lat', 'user_lng', 'date_created')
        read_only_fields = ('user', 'post_files', 'showcase_comment', 'set_lat', 'set_lng')


    def get_bookmarked(self, obj):
        user = self.context["user"]
        return Activity.objects.filter(user=user, content_type=self.post_content_type, object_id=obj.id, activity_type=Activity.BOOKMARK).exists()

class PostLISTSerializer(PostSerializer):
    user__username = serializers.CharField(source="user.username")
    user__title = serializers.CharField(source="user.title")
    user__profile_photos = serializers.JSONField(source="user.profile_photos")
    dish__id = serializers.SerializerMethodField()
    dish__name = serializers.SerializerMethodField()
    dish__is_favourite = serializers.SerializerMethodField()
    restaurant__id = serializers.SerializerMethodField()
    restaurant__name = serializers.SerializerMethodField()
    restaurant__location = serializers.SerializerMethodField()
    files = PostFileDETAILSerializer(source="post_files", many=True)
    showcase_comment = PostCommentDETAILSerializer()
    is_liked = serializers.SerializerMethodField()

    class Meta(PostSerializer.Meta):
        fields = PostSerializer.Meta.fields+('user__username',
            'user__title', 'user__profile_photos', 'dish__id', 'dish__name',
            'dish__is_favourite', 'restaurant__id', 'restaurant__name',
            'restaurant__location', 'files', 'is_liked', 'likes_count')

    def get_dish__id(self, obj):
        if obj.dish:
            return obj.dish.id
        return None

    def get_dish__name(self, obj):
        if obj.dish:
            return obj.dish.name
        return None

    def get_restaurant__id(self, obj):
        if obj.restaurant:
            return obj.restaurant.id
        return None

    def get_restaurant__name(self, obj):
        if obj.restaurant:
            return obj.restaurant.name
        return None

    def get_restaurant__location(self, obj):
        if obj.restaurant:
            return obj.restaurant.location
        return None

    def get_dish__is_favourite(self, obj):
        dish = obj.dish
        user = self.context["user"]
        return dish in user.favourite_dishes.all()

    def get_is_liked(self, obj):
        user = self.context["user"]
        return user.liked_posts.filter(pk=obj.pk).exists()

class PostDETAILSerializer(PostLISTSerializer):
    user = UserSerializer()


class PostCREATESerializer(PostSerializer):
    # files = _FileSerializer(many=True, required=True)
    files = serializers.ListField()
    class Meta(PostSerializer.Meta):
        fields = PostSerializer.Meta.fields+('files',)
        read_only_fields = PostSerializer.Meta.read_only_fields+('post_files',)

    def to_representation(self, instance):
        serializer = PostDETAILSerializer(instance=instance, context=self.context)
        return serializer.data

    def validate(self, attrs):
        user = self.context["user"]
        attrs["user"] = user
        dish = attrs.get("dish", None)
        restaurant = attrs.get("restaurant", None)
        other_restaurant = attrs.get("other_restaurant", None)
        other_dish = attrs.get("other_dish", None)
        if dish:
            restaurant = attrs["restaurant"] = dish.restaurant
        if not (restaurant or other_restaurant):
            raise serializers.ValidationError("restaurant is required")
        if not (dish or other_dish):
            raise serializers.ValidationError("dish is required")
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        files = validated_data.pop("files", [])
        tags = validated_data.pop("tags", [])
        instance = Post.objects.create(**validated_data)

        post_files = [{
            "post": instance.id,
            "file": file,
        } for file in files]

        serializer = PostFileCREATESerializer(data=post_files, many=True)
        if serializer.is_valid():
            serializer.save()
        else:
            raise serializers.ValidationError(serializer.errors)
        return instance

# class PostCREATESerializer(PostSerializer):
#     files = serializers.ListField(required=False)
#     class Meta(PostSerializer.Meta):
#         fields = PostSerializer.Meta.fields+('files',)
#         read_only_fields = PostSerializer.Meta.read_only_fields+('post_files',)
#
#     def to_representation(self, instance):
#         serializer = PostDETAILSerializer(instance=instance, context=self.context)
#         return serializer.data
#
#     def validate(self, attrs):
#         user = self.context["user"]
#         attrs["user"] = user
#         attrs["user_lat"] = user.current_location.lat
#         attrs["user_lng"] = user.current_location.lng
#         return attrs
#
#     @transaction.atomic
#     def create(self, validated_data):
#         files = validated_data.pop("files", [])
#         tags = validated_data.pop("tags", [])
#         restaurant = validated_data.get("restaurant", False)
#         dish = validated_data.get("dish", "")
#         rq = restaurant and Restaurant.objects.filter(google_id=restaurant["id"])
#         if rq and rq.exists():
#             validated_data["restaurant"] = rq[0]
#         elif restaurant:
#             data = {
#                 "google_id": restaurant["id"],
#                 "google_place_id": restaurant["place_id"],
#                 "google_rating": restaurant["rating"],
#                 "name": restaurant["name"],
#                 "address": restaurant["vicinity"],
#                 "lat": restaurant["geometry"]["location"]["lat"],
#                 "lng": restaurant["geometry"]["location"]["lng"]
#             }
#             validated_data["restaurant"] = Restaurant.objects.create(**data)
#         dq = dish and Dish.objects.filter(name__iexact=dish)
#         if dq and dq.exists():
#             validated_data["dish"] = dq[0]
#         elif dish:
#             validated_data["dish"] = Dish.objects.create(name=dish)
#         instance = Post.objects.create(**validated_data)
#         for file in files:
#             data = {
#                 "post": instance.id,
#                 "file": file,
#             }
#             serializer = PostFileCREATESerializer(data=data)
#             if serializer.is_valid():
#                 serializer.save()
#             else:
#                 raise serializers.ValidationError(serializer.errors)
#         return instance

class PostUPDATESerializer(PostSerializer):
    pass

class PostPATCHSerializer(PostSerializer):

    def to_representation(self, instance):
        serializer = PostLISTSerializer(instance=instance, context=self.context)
        return serializer.data

class PostDELETESerializer(PostSerializer):
    pass

class PostActivitySerializer(serializers.ModelSerializer):
    post_content_type = ContentType.objects.get_for_model(Post)
    post = serializers.PrimaryKeyRelatedField(source="object_id", queryset=Post.objects.all())
    class Meta:
        model = Activity
        fields = ('id', 'user', 'activity_type', 'post', 'date_modified')
        read_only_fields = ("user", "content_type")

class PostActivityDETAILSerializer(PostActivitySerializer):
    pass

class PostActivityLISTSerializer(PostActivitySerializer):
    pass

class PostActivityCREATESerializer(PostActivitySerializer):
    UP_VOTE_DOWN_VOTE = [Activity.UP_VOTE, Activity.DOWN_VOTE]
    post = serializers.PrimaryKeyRelatedField(queryset=Post.objects.all())
    activity_type = serializers.CharField(required=True)

    def to_representation(self, instance):
        serializer = PostActivityDETAILSerializer(instance=instance, context=self.context)
        return serializer.data

    def validate_activity_type(self, activity_type):
        if not activity_type in [Activity.UP_VOTE, Activity.DOWN_VOTE, Activity.RECOMMEND, Activity.BOOKMARK]:
            raise serializers.ValidationError("Unknow Activity")
        return activity_type

    def validate(self, attrs):
        post = attrs["post"]
        if post.user==self.context["user"] and attrs["activity_type"] in self.UP_VOTE_DOWN_VOTE:
            raise serializers.ValidationError("Oh! You cannot upvote/downvote your own Post")
        attrs["user"] = self.context["user"]
        attrs["content_type"] = self.post_content_type
        return attrs

    def create(self, validated_data):
        user = validated_data["user"]
        post = validated_data.pop("post")
        validated_data["object_id"] = post.id
        activity_type = validated_data["activity_type"]
        paq = None
        if activity_type in self.UP_VOTE_DOWN_VOTE:
            paq = Activity.objects.filter(user=user, content_type=self.post_content_type, object_id=post.id, activity_type__in=self.UP_VOTE_DOWN_VOTE)
        else:
            paq = Activity.objects.filter(user=user, content_type=self.post_content_type, object_id=post.id, activity_type=activity_type)
        if not paq.exists():
            instance = Activity.objects.create(**validated_data)
        else:
            instance = paq[0]
            if activity_type == instance.activity_type:
                instance.delete()
            else:
                instance.activity_type=activity_type
                instance.save()
        return instance

class PostActivityPUTSerializer(PostActivitySerializer):
    pass

class PostActivityPATCHSerializer(PostActivitySerializer):
    pass

class PostActivityDELETESerializer(PostActivitySerializer):
    pass


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = ('id', 'user', 'activity_type', 'content_type', 'object_id',
            'content_object', 'date_created')

class BaseFileGenerateSerializer(serializers.Serializer):
    extension = None
    FILE_EXTENSIONS = (".csv", ".xls", ".json",)
    FILE_ACTIONS = []
    action = serializers.CharField(max_length=None, required=True)

    def validate_action(self, action):
        if not action in self.FILE_ACTIONS:
            raise serializers.ValidationError("Action not allowed.")
        return action

    def create(self, validated_data):
        action = validated_data["action"]
        data = eval('self.'+action+'(validated_data)')
        return data

class SearchSerializer(serializers.Serializer):
    type = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    pic = serializers.SerializerMethodField()

    class Meta:
        fields = ('type', 'id', 'name', 'pic')

    def get_type(self, obj):
        return obj.__class__.__name__.lower()

    def get_id(self, obj):
        return obj.id

    def get_name(self, obj):
        return obj.name

    def get_pic(self, obj):
        obj_type = self.get_type(obj)
        pic = None
        if obj_type=="user":
            pic = obj.profile_photos["50x50"] if obj.profile_photos else None
        elif obj_type == "dish":
            pic = obj.photos["50x50"] if obj.resized_photos else None
        elif obj_type == "restaurant":
            pic = obj.logos["50x50"] if obj.resized_logos else None
        return pic

class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ('id', 'user', 'rating', 'description', 'date_created')

class FeedbackLISTSerializer(FeedbackSerializer):
    pass

class FeedbackDETAILSerializer(FeedbackSerializer):
    pass

class FeedbackCREATESerializer(FeedbackSerializer):
    class Meta(FeedbackSerializer.Meta):
        read_only_fields = ('user',)

    def validate_rating(self, rating):
        if rating < 0 or rating > 5:
            raise serializers.ValidationError("Nice trick!")
        return rating

    def validate(self, attrs):
        attrs["user"] = self.context["user"]
        return attrs

class FeedbackUPDATESerializer(FeedbackSerializer):
    pass

class FeedbackPATCHSerializer(FeedbackSerializer):
    pass

class FeedbackDELETESerializer(FeedbackSerializer):
    pass

class DataStoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataStore
        fields = '__all__'
