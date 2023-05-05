from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views import View
from django.http import Http404
from django.contrib import messages
from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth import login, logout, authenticate
from django.core.exceptions import ValidationError
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import DetailView, ListView, CreateView, FormView, UpdateView, DeleteView
from django.shortcuts import get_list_or_404, get_object_or_404
from django.forms import formset_factory
from django.forms import inlineformset_factory
from django.db import transaction
from rest_framework import generics
from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import JSONParser
from .models import *
from .mixins import *

def angular(request):
    return render(request, 'angular.html')

class ActivateAccountView(View):
    def get(self, request, uidb64, token):
        try:
            uid = force_text(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and account_activation_token.check_token(user, token):
            user.is_active = True
            user.email_confirmed = True
            user.save()
            same_email_users = User.objects.filter(email=user.email).exclude(id=user.id)
            for u in same_email_users:
                u.email_confirmed=False
                u.save()
            return redirect(reverse_lazy('login_')+'?activated=true')
        else:
            raise Http404
