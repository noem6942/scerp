"""
Django settings for scerp project.

Generated by 'django-admin startproject' using Django 4.2.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""
# settings.py
import os
from pathlib import Path


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    # Windows needs to load env in settings
    from .load_env_windows import SECRET_KEY as key
    SECRET_KEY = key

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG") == "True"  # Convert the string 'True' to a boolean value

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# Application definition
# GUI looked at jazzmin, grappelli and baton but all failed

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_admin_action_forms',  # Extension for the Django admin panel
    'core',
    'home',
    'accounting',
    'billing',
    'crm',
    'meeting',
    'vault'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'core.middleware.TenantMiddleware',  # Control tenant
]

ROOT_URLCONF = 'scerp.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'scerp.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Session settings
# SESSION_ENGINE = 'django.contrib.sessions.backends.db'  # Using database-backed sessions
# SESSION_COOKIE_AGE = 3600  # One hour session expiration


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'de-ch'
LANGUAGE_CODE_PRIMARY = 'de'  # used for accounting

TIME_ZONE = 'Europe/Zurich'

USE_I18N = True

USE_TZ = True

# List of languages supported by your project
LANGUAGES = [
    ('de', 'Deutsch'),
    ('fr', 'French'),
    ('it', 'Italiano'),
    ('en', 'English'),
]

# Locale path where your translation files will be stored
LOCALE_PATHS = [
    BASE_DIR / 'locale',  # Make sure this directory exists
]

USE_THOUSAND_SEPARATOR = True
THOUSAND_SEPARATOR = "'"

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [BASE_DIR / 'static']

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Media
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Docs
DOCS_ROOT = os.path.join(BASE_DIR, 'docs/build/html')
DOCS_SOURCE = os.path.join(BASE_DIR, 'docs/source')
DOCS_ACCESS = 'public'  # 'staff' or 'public', depending on who should have access


# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {  # Default logger for all modules
        'handlers': ['console'],
        'level': 'INFO',  # Set a default level
    },
    'loggers': {
        'django': {  # Django-specific logging
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,  # Prevent double logging
        },
        'core': {  # Example app-specific logger
            'handlers': ['console'],
            'level': 'DEBUG',  # Adjust level as needed
            'propagate': False,
        },
    },
}


# Ckeditor
CKEDITOR_UPLOAD_PATH = "uploads/"
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'Custom',
        'toolbar_Custom': [
            {'name': 'clipboard', 'items': ['Cut', 'Copy', 'Paste', 'PasteText', 'PasteFromWord']},
            {'name': 'editing', 'items': ['Find', 'Replace', 'SelectAll']},
            {'name': 'basicstyles', 'items': ['Bold', 'Italic', 'Underline']},
            # Add other toolbar options as needed
        ],
        'height': 300,
        'extraPlugins': ','.join(['uploadimage', 'image2']),
    },
}


# mine
ADMIN_ROOT = 'scerp'
ADMIN_ACCESS_ALL = True  # Admin can access all clients
LOGO = '/static/img/default-logo.png'
