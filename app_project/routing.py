from django.conf import settings
from rest_framework import exceptions
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
import app_socket.routing
from django.db import close_old_connections
from django.contrib.auth.models import AnonymousUser
from app.models import User, TokenBlackList
import jwt
from asgiref.sync import sync_to_async, async_to_sync
from channels.db import database_sync_to_async

@database_sync_to_async
def get_user(token):
    if token is None or token == "null" or token.strip() == "" or TokenBlackList.objects.filter(token=token).exists():
        return AnonymousUser()
    decoded = jwt.decode(token, settings.SECRET_KEY)
    username = decoded['username']
    user_obj =  User.objects.filter(phone_number=username).first() or User.objects.filter(username=username).first()
    return user_obj

def isTokenBlackListed(token):
    return TokenBlackList.objects.filter(token=token).exists()

class TokenAuthMiddlewareInstance:
    """
    Token authorization middleware for Django Channels 2
    """

    def __init__(self, scope, middleware):
        self.middleware = middleware
        self.scope = dict(scope)
        self.inner = self.middleware.inner

    async def __call__(self, receive, send):
        close_old_connections()
        headers = dict(self.scope['headers'])
        query = dict((x.split('=') for x in self.scope['query_string'].decode().split("&")))
        token = query['token']

        self.scope['user'] = await get_user(token)
        self.scope["token"]=token
        self.inner = self.inner(self.scope)
        return await self.inner(receive, send)

class TokenAuthMiddleware:
    """
    Token authorization middleware for Django Channels 2
    see:
    https://channels.readthedocs.io/en/latest/topics/authentication.html#custom-authentication
    """

    def __init__(self, inner):
        self.inner = inner

    def __call__(self, scope):
        return TokenAuthMiddlewareInstance(scope, self)

TokenAuthMiddlewareStack = lambda inner: TokenAuthMiddleware(AuthMiddlewareStack(inner))

application = ProtocolTypeRouter({
    # (http->django views is added by default)
    'websocket': TokenAuthMiddlewareStack(
        URLRouter(
            app_socket.routing.websocket_urlpatterns
        )
    ),
})
