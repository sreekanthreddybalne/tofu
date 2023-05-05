# docsocket/consumers.py
from channels.generic.websocket import WebsocketConsumer, AsyncWebsocketConsumer
import json
from channels.consumer import SyncConsumer
from channels.exceptions import StopConsumer
from django.shortcuts import get_list_or_404, get_object_or_404
from app.models import *
from app import choices
from .settings import *
from .utils import get_user_room, broadcast_data
from api.serializers import *
from asgiref.sync import async_to_sync, sync_to_async
import inspect, sys
from channels.db import database_sync_to_async

class SocketConsumer(AsyncWebsocketConsumer):
    user = None
    async def connect(self):
        self.user = self.scope["user"]
        if TokenBlackList.objects.filter(token=self.scope["token"]).exists():
            self.close()
        self.user_room_name = get_user_room(self.user.id)

        await self.accept()
        # Join user_room group
        await self.channel_layer.group_add(
            self.user_room_name,
            self.channel_name
        )

    async def disconnect(self, close_code):
        # Leave user_room group
        await self.channel_layer.group_discard(
            self.user_room_name,
            self.channel_name
        )
        raise StopConsumer()


    async def receive(self,text_data):
        text_data_json = json.loads(text_data)
        event_type = text_data_json['event_type']
        data = text_data_json['data']
        message = {
        'event_type': event_type,
        'data': None,
        'errors': None
        }
        if event_type=="chat-message":
            roomId = data.get("room", None)
            content = data.get("content", None)
            file = data.get("file", None)
            data = {
                "sender": self.user.id,
                "room": roomId,
                "content": content,
                "file": file,
            }
            serializer = MessageCREATESerializer(data=data)
            if serializer.is_valid():
                messageData=serializer.save()
                message["event_type"]=event_type
                message["data"] = serializer.data
                room = Room.objects.get(pk=roomId)
                for user in room.users.all():
                    await self.channel_layer.group_send(
                        get_user_room(user.id),
                        {
                            'type': "send_notif",
                            'message': message
                        }
                    )
            else:
                message["errors"]=serializer.errors
                await self.send(text_data=json.dumps({
                    'message': message
                }))
        elif event_type=="notification:seen":
            message["event_type"]=event_type
            Notification.objects.filter(status=NOTIFICATION_STATUS_SENT).update(status=NOTIFICATION_STATUS_SEEN)
            await self.channel_layer.group_send(
                self.user_room_name,
                {
                    'type': "send_notif",
                    'message': message
                }
            )


    async def send_notif(self, event):
        message =  event['message']
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))
