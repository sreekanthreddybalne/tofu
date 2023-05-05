from django.conf import settings
from django.contrib.auth import login
from django.utils.translation import gettext as _
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework import authentication, exceptions, serializers
from django.contrib.auth import authenticate, get_user_model, login


from rest_framework_jwt.serializers import JSONWebTokenSerializer
from rest_framework_jwt.settings import api_settings
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.utils.crypto import get_random_string
from string import ascii_lowercase, digits
import json

def is_json(myjson):
    try:
        json_object = json.loads(myjson)
    except ValueError as e:
        return False
    return True

def get_random_id():
    return get_random_string(5, ascii_lowercase + digits)

class CustomPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'records_per_page'
    max_page_size = 1000

    def get_paginated_response(self, data):
        return Response({
            'next_page_url': self.get_next_link(),
            'previous_page_url': self.get_previous_link(),
            'total_no_of_records': self.page.paginator.count,
            'records_per_page': self.page.paginator.per_page,
            'total_pages': self.page.paginator.num_pages,
            'page_number': self.page.number,
            'next_page_number': self.page.number+1 if self.page.paginator.num_pages>self.page.number else None,
            'results': data
        })





class appBasicAuthentication(BasicAuthentication):

    def authenticate(self, request):
        username = request.data.get('username', None)
        password = request.data.get('password', None)

        if not username or not password:
            raise exceptions.AuthenticationFailed(_('No credentials provided.'))

        credentials = {
            get_user_model().USERNAME_FIELD: username,
            'password': password
        }

        user = authenticate(**credentials)

        if user is None:
            raise exceptions.AuthenticationFailed(_('Invalid username/password.'))

        if not user.is_active:
            raise exceptions.AuthenticationFailed(_('User inactive or deleted.'))

        #user, _ = super(appBasicAuthentication, self).authenticate(request)

        #return user, _
        return (user, None)  # authentication successful
