from django.contrib.auth.base_user import BaseUserManager
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.template.loader import render_to_string
import random
from django.db.models.aggregates import Count
from random import randint
from django.db import models
from .tokens import account_activation_token

class RandomQuerySet(models.QuerySet):
    def random(self):
        count = self.aggregate(count=Count('id'))['count']
        random_index = randint(0, count - 1)
        return self.all()[random_index]

class UserManager(BaseUserManager):
    use_in_migrations = True

    def get_queryset(self):
        return RandomQuerySet(self.model, using=self._db)  # Important!

    def _create_user(self, email, password, **extra_fields):
        """
        Creates and saves a User with the given username, email and password.
        """
        try:
            validate_email(email)
            valid_email = True
        except ValidationError:
            valid_email = False
        if not valid_email:
            raise ValueError('Valid Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_staff', True)

        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)



class RiskManager(models.Manager):
    use_in_migrations = True
    user_count = 0
    user = None
    user_id_list = None
    title = None
    is_private = None

    def get_field(self, risk_id, field_id):
        risk = self.get(pk=risk_id)
        fields = risk.fields
        for f in risk.fields:
            if f["id"]==field_id:
                return f
        return None


class BuzzerQuerySet(models.QuerySet):
    def random(self):
        count = self.aggregate(count=Count('id'))['count']
        random_index = randint(0, count - 1)
        return self.all()[random_index]


class BuzzerManager(models.Manager):
    def get_queryset(self):
        return BuzzerQuerySet(self.model, using=self._db)  # Important!

    def random(self):
        count = self.aggregate(count=Count('id'))['count']
        random_index = randint(0, count - 1)
        return self.all()[random_index]
