import itertools
from django.utils.crypto import get_random_string
from string import ascii_lowercase, digits
from .settings import CODE_LENGTH, CAMPAIGN_TASK_BATCH_CODE_LENGTH, OTP_LENGTH, ROOM_CODE_LENGTH, USERNAME_MIN_LENGTH, USERNAME_MAX_LENGTH
from .models import *
from . import choices
from .tasks import task_send_confirmation_mail, task_send_welcome_mail
from django.utils.text import slugify
secret_chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
chars = ascii_lowercase
charsdigits =  ascii_lowercase + digits
otp_chars = digits

def generate_otp():
    return get_random_string(OTP_LENGTH, otp_chars)

def delete_users():
    User.objects.filter(is_superuser=False).exclude(email="AnonymousUser").delete()

def create_super_users():
    from api.serializers import UserCREATESerializer
    USERS = [
        {"email": "whitehathackersree@gmail.com", "password": "D.t9676768131", "role": choices.ROLE_ADMIN },
        {"email": "sreekanthreddytrnt@gmail.com", "password": "D.t9676768131", "role": choices.ROLE_MARKETING_MANAGER },
        {"email": "godknowsnothingaboutme@gmail.com", "password": "D.t9676768131", "role": choices.ROLE_ADVISOR_MANAGER },
        {"email": "redcarpetflew@gmail.com", "password": "D.t9676768131", "role": choices.ROLE_ADVISOR },
        {"email": "blackhat9912509109@gmail.com", "password": "D.t9676768131", "role": choices.ROLE_PROSPECT },
    ]
    for u in USERS:
        serializer = UserCREATESerializer(data=u)
        if serializer.is_valid():
            serializer.save()
        else:
            raise serializers.ValidationError(serializer.errors)
    print("Done Creating Users")

def get_secret_key():
    """
    Return a 50 character random string usable as a SECRET_KEY setting value.
    """
    return get_random_string(50, secret_chars)


def generate_campaign_task_batch_code():
    from app.models import CampaignTaskBatch
    codes = CampaignTaskBatch.objects.values_list('code', flat=True)
    while True:
        value = get_random_string(CAMPAIGN_TASK_BATCH_CODE_LENGTH, digits)
        if value not in codes:
            return value

def generate_room_code():
    from app.models import Room
    codes = Room.objects.values_list('code', flat=True)
    while True:
        value = get_random_string(ROOM_CODE_LENGTH, charsdigits)
        if value not in codes:
            return value


def generate_code(prefix='P'):
    from app.models import User
    codes = User.objects.values_list('code', flat=True)
    while True:
        value = prefix + get_random_string(CODE_LENGTH, digits)
        if value not in codes:
            return value
