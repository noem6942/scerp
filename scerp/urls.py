# scerp/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from core.views import home, test
from scerp.admin import admin_site

GUI_ROOT = settings.ADMIN_ROOT


urlpatterns = [   
    path('admin/', admin.site.urls),  # Default Django admin 
    path(GUI_ROOT + '/', admin_site.urls),  # Use the custom admin site
    path('', home, name='home'), 
    path('test/', test, name='test'), 
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
