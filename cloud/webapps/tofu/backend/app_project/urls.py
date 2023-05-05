from django.urls import path, include
from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
admin.autodiscover()

urlpatterns = [
    path(r'api-auth/', include('rest_framework.urls')),
    path(r'admin/', admin.site.urls),
    path(r'api/', include('api.urls')),
    path(r'', include('app.urls')),
]

if settings.DEBUG:
    urlpatterns = static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)+urlpatterns

urlpatterns =  staticfiles_urlpatterns() + urlpatterns
