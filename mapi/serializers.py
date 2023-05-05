from rest_framework import serializers
import os
from django.utils.translation import ugettext_lazy as _
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
import json
from django.http import HttpResponse
from app.models import Post, Activity
