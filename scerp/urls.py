"""
scerp/urls.py
"""
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.views.generic import RedirectView

from scerp.admin_site import admin_site

GUI_ROOT = settings.ADMIN_ROOT


# Define media serving only for development
if settings.DEBUG:
    media_patterns = static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    media_patterns = []  # In production, served by the web server


urlpatterns = media_patterns + [
    # API endpoint for the time app
    path('api/time/', include('time_app.urls')),

    # Custom admin site using GUI_ROOT
    path(f'{GUI_ROOT}/', admin_site.urls),

    # Meeting app routes
    path('meeting/page/', include('meeting.urls')),

    # Redirect from login.html to GUI_ROOT
    path('login.html', RedirectView.as_view(
        url=f'/{GUI_ROOT}/', permanent=True), name='login_redirect'),

    # Documentation app routes, we do not have a HomeView
    path('', include('docs.urls')),
]
