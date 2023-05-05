from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.urls import reverse_lazy
from django.contrib.auth import views as auth_views
from django.contrib import admin
from app import views as vw

admin.site.site_title = 'Wealth Management Admin'
admin.site.site_header = 'Wealth Management Administration'

urlpatterns = [
    path(r'activate/<uidb64>/<token>/', vw.ActivateAccountView.as_view(), name='activate'),
    re_path(r'', vw.angular, name='tofuApp'),
]
