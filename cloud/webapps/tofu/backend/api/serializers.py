from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
import os
import json
import re
import math
phone_number_regex = re.compile("^[6789]\d{9}$")
from django.utils.translation import ugettext_lazy as _
from django.db import transaction
from django.db.transaction import on_commit
from django.urls import reverse_lazy
from guardian.shortcuts import assign_perm
from decimal import *
from app.models import *
from app.choices import *
from app.tokens import random_string_generator
from app.tasks import task_send_activation_mail, task_send_confirmation_mail
from api.custom_fields import Base64ImageField
from app.settings import PASSWORD_MIN_LENGTH, OTP_LENGTH, OTP_TRIES, OTP_EXPIRY
from django.conf import settings
from django.utils import timezone
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
import json
import csv
import pandas as pd
from django.http import HttpResponse
from wsgiref.util import FileWrapper
from django.core.files.uploadedfile import InMemoryUploadedFile
import zipfile
from io import StringIO
from api.utils import is_json
from app.utils import get_secret_key, generate_code, generate_campaign_task_batch_code
import app.choices as choices


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
        check_otp(otp, phone_number)
        return attrs

class AuthUserSerializer(serializers.ModelSerializer):
    is_authenticated = serializers.BooleanField(default=True)
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'phone_number', 'profile_photos', 'address',
        'first_name', 'last_name', 'full_name', 'title', 'gender', 'country', 'city',
        'state', 'followers_count', 'is_authenticated')

class AuthUserPOSTSerializer(serializers.ModelSerializer):
    is_authenticated = serializers.BooleanField(default=True)
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone_number', 'address', 'is_authenticated')


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

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'full_name', 'title',
            'short_description',
            'gender', 'photo', 'profile_photos', 'phone_number', 'age',
            'address', 'zip_code', 'city', 'country',
            'state', 'points', 'followers_count', 'url', 'date_created')
        extra_kwargs = {
            'email': {"error_messages":{
                "required": "email is required",
                "blank": "email is required",
                "invalid": "email is invalid",
                }
            },
            'password': {"error_messages":{
                "required": "password is required",
                "blank": "password is required",
                "invalid": "password is invalid",
                }
            },
        }

class UserDETAILSerializer(UserSerializer):
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
    skip_password = False

    def __init__(self, skip_password=False, *args, **kwargs):
        super(UserCREATESerializer, self).__init__(*args, **kwargs)
        self.skip_password=skip_password;
        if self.skip_password:
            self.fields['password'] = serializers.CharField(required=False)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields+('password', )
        extra_kwargs = {
            'email': {"error_messages":{
                "required": "email is required",
                "blank": "email is required",
                "invalid": "email is invalid",
                }
            },
            'password': {"error_messages":{
                "required": "password is required",
                "blank": "password is required",
                "invalid": "password is invalid",
                }
            }
        }


    def validate_password(self, value):
        if self.skip_password:
            return get_secret_key()
        if not self.skip_password and len(value)<PASSWORD_MIN_LENGTH :
            raise serializers.ValidationError("password must contain atleast 8 characters..")
        return value

    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create(**validated_data)
        if self.skip_password:
            validated_data["password"] = get_secret_key()
        user.set_password(validated_data['password'])
        user.is_active=True
        user.save()
        return user


class UserUPDATESerializer(UserSerializer):
    is_authenticated = serializers.BooleanField(default=True, read_only=True)
    photo = Base64ImageField(
        max_length=None, use_url=True, required=False
    )

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ('is_authenticated',)
        read_only_fields = ('id', 'email', 'is_authenticated')

    def to_representation(self, instance):
        serializer = UserDETAILSerializer(instance=instance)
        return serializer.data

    @transaction.atomic
    def update(self, instance, validated_data):
        instance.__dict__.update(**validated_data)
        instance.save()
        instance = super().update(instance, validated_data)
        return instance

class BadgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Badge
        fields = ('id', 'name', 'short_description', 'description', 'date_created')


class FriendshipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Friendship
        fields = ('id', 'creator', 'friend', 'date_created')

class ProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provider
        fields = ('id', 'name', 'url', 'logo', 'background', 'date_created')

class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ('id', 'name', 'description', 'coordinates', 'address',
            'zip_code', 'city', 'state', 'country', 'map_data',
            'how_to_get_there', 'opening_hours', 'rating', 'average_cost',
            'average_cost_per_no_of_persons', 'admin', 'date_created')

class RestaurantPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantPhoto
        fields = ('id', 'file', 'title', 'description', 'order',
            'date_created')

class RestaurantRatingTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantRatingType
        fields = ('id', 'name', 'date_created')

class RestaurantRatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantRating
        fields = ('id', 'restaurant', 'rating_type', 'stars', 'date_created')

class DishTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DishType
        fields = ('id', 'name', 'date_created')

class DishTypeDETAILSerializer(DishTypeSerializer):
    pass

class DishTypeLISTSerializer(DishTypeSerializer):
    pass

class DishTypeCREATESerializer(DishTypeSerializer):

    def validate_name(self, name):
        if DishType.objects.filter(name=name).exists():
            raise serializers.ValidationError("Dish Type "+name+" already exists.")
        return name

class DishTypeUPDATESerializer(DishTypeSerializer):
    pass

class DishTypePATCHSerializer(DishTypeSerializer):
    pass

class DishTypeDELETESerializer(DishTypeSerializer):
    pass

class DishSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dish
        fields = ('id', 'restaurant', 'dish_type', 'name', 'description',
            'date_created')

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
        fields = ('id', 'name', 'short_description', 'description',
            'date_created')
class PostTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostType
        fields = ('id', 'name', 'date_created')

class PostTypeDETAILSerializer(PostTypeSerializer):
    pass

class PostTypeLISTSerializer(PostTypeSerializer):
    pass

class PostTypeCREATESerializer(PostTypeSerializer):
    pass

class PostTypeUPDATESerializer(PostTypeSerializer):
    pass

class PostTypePATCHSerializer(PostTypeSerializer):
    pass

class PostTypeDELETESerializer(PostTypeSerializer):
    pass

class PostFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostFile
        fields = ('id', 'post', 'file', 'order', 'date_created')

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


class PostCommentSerializer(serializers.ModelSerializer):
    post_comment_content_type = ContentType.objects.get_for_model(PostComment)
    upvoted = serializers.SerializerMethodField()
    class Meta:
        model = PostComment
        fields = ('id', 'user', 'post', 'parent', 'description', 'upvoted', 'upvotes_count', 'date_created')
        read_only_fields = ('user', )

    def get_upvoted(self, obj):
        user = self.context["user"]
        return Activity.objects.filter(user=user, content_type=self.post_comment_content_type, object_id=obj.id, activity_type=Activity.UP_VOTE).exists()

class PostCommentDETAILSerializer(PostCommentSerializer):
    user = UserSerializer()

class PostCommentLISTSerializer(PostCommentDETAILSerializer):
    pass

class PostCommentCREATESerializer(PostCommentSerializer):

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
    class Meta:
        model = Post
        fields = ('id', 'user', 'post_type', 'post_files', 'restaurant', 'dish', 'question',
            'description', 'geolocation', 'rating', 'tags', 'swiggy_link',
            'zomato_link', 'showcase_comment', 'upvotes_count', 'downvotes_count',
            'upvoted', 'date_created')
        read_only_fields = ('user', 'showcase_comment',)

    def get_upvoted(self, obj):
        user = self.context["user"]
        return Activity.objects.filter(user=user, content_type=self.post_content_type, object_id=obj.id, activity_type=Activity.UP_VOTE).exists()


class PostDETAILSerializer(PostSerializer):
    user = UserSerializer()
    post_files = PostFileDETAILSerializer(many=True)
    showcase_comment = PostCommentDETAILSerializer()

class PostLISTSerializer(PostDETAILSerializer):
    pass

class PostCREATESerializer(PostSerializer):
    files = serializers.ListField(required=False)
    class Meta(PostSerializer.Meta):
        fields = PostSerializer.Meta.fields+('files',)
        read_only_fields = ('user', 'post_files')

    def to_representation(self, instance):
        serializer = PostDETAILSerializer(instance=instance, context=self.context)
        return serializer.data

    def validate(self, attrs):
        attrs["user"] = self.context["user"]
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        files = validated_data.pop("files", [])
        tags = validated_data.pop("tags", [])
        instance = Post.objects.create(**validated_data)
        for file in files:
            data = {
                "post": instance.id,
                "file": file,
            }
            serializer = PostFileCREATESerializer(data=data)
            if serializer.is_valid():
                serializer.save()
            else:
                raise serializers.ValidationError(serializer.errors)
        return instance

class PostUPDATESerializer(PostSerializer):
    pass

class PostPATCHSerializer(PostSerializer):
    pass

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
