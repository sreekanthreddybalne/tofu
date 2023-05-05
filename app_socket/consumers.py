# docsocket/consumers.py
from channels.generic.websocket import WebsocketConsumer, AsyncWebsocketConsumer
import json
from channels.consumer import SyncConsumer
from channels.exceptions import StopConsumer
from django.shortcuts import get_list_or_404, get_object_or_404
from app.models import *
from app import choices
from .settings import *
from .utils import get_user_room, get_post_room, broadcast_data
from api.serializers import PostCommentCREATESerializer
from asgiref.sync import async_to_sync, sync_to_async
import inspect, sys
from channels.db import database_sync_to_async
from django.test.client import RequestFactory

dummy_request = RequestFactory().post('/dummy')

class PostCommentConsumer(WebsocketConsumer):
    user = None
    def websocket_connect(self, data):
        self.user = self.scope["user"]
        self.post_id = self.scope["url_route"]["kwargs"]["id"]
        if(TokenBlackList.objects.filter(token=self.scope["token"]).exists()):
            self.close()
        self.post_room_name = get_post_room(self.post_id)

        self.accept()
        # Join user_room group
        self.channel_layer.group_add(
            self.post_room_name,
            self.channel_name
        )

    def websocket_disconnect(self, close_code):
        # Leave user_room group
        self.channel_layer.group_discard(
            self.post_room_name,
            self.channel_name
        )
        raise StopConsumer()


    def websocket_receive(self, payload):
        context = {"request": dummy_request, "user": self.user }
        payload["post"] = self.post_id
        serializer = PostCommentCREATESerializer(data=payload, context=context)
        if serializer.is_valid():
            instance = serializer.save()
            self.channel_layer.group_send(
                self.post_room_name,
                serializer.data
            )

    def send_comment(self, event):
        message =  event['message']
        # Send message to WebSocket
        self.send(text_data=json.dumps({
            'message': message
        }))
