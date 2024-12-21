"""
scerp/urls.py
"""
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.views.generic import RedirectView

from scerp.admin import admin_site

GUI_ROOT = settings.ADMIN_ROOT


# Define media serving only for development
if settings.DEBUG:
    media_patterns = static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    media_patterns = []  # In production, served by the web server

urlpatterns = media_patterns + [
    path(GUI_ROOT + '/', admin_site.urls),  # Custom admin site
    path('meeting/page/', include('meeting.urls')),
    path('login.html', RedirectView.as_view(
        url=f'/{GUI_ROOT}/', permanent=True), name='login_redirect'),
    path('', include('docs.urls')),  # Docs routes
]
