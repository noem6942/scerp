"""
Django settings for scerp project.

To check:
    Hosting: https://oriented.net/hosting/python
"""
# settings.py
import environ
import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialize environment variables
env = environ.Env()

# Explicitly specify the path to the .env file
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY", default=None)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=False)

# ALLOWED_HOSTS from environment variable or fallback to an empty string
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost'])

# Application definition
# GUI looked at jazzmin, grappelli and baton but all failed

INSTALLED_APPS = [
    # django
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # plugins
    'django_admin_action_forms',  # Extension for the Django admin panel
    'bootstrap4',
    'import_export',
    'rest_framework',    
    
    # mine
    'asset',
    'core',    
    'home',
    'accounting',
    'billing',
    'crm',
    'meeting',
    'time_app',
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
if env.bool("TESTING", default=False):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:'
        }
    }
elif 'sqlite' in env('ENGINE'):
    DATABASES = {
        'default': {
            'ENGINE': env('ENGINE'),
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': env('ENGINE'),
            'NAME': env('DB_NAME'),
            'USER': env('DB_USER'),
            'PASSWORD': env('DB_PASSWORD'),
            'HOST': env('DB_HOST'),
            'PORT': env('DB_PORT', default='3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
            },            
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
LANGUAGE_CODE_PRIMARY = 'de'  # used for multi language display

TIME_ZONE = 'Europe/Zurich'

USE_I18N = True

USE_TZ = True

# List of languages supported by your project
LANGUAGES = [
    ('de', 'Deutsch'),
    ('en', 'English'),
    ('fr', 'French'),
    ('it', 'Italiano'),
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
APPLICATION_NAME = 'SC-ERP'
ADMIN_ACCESS_ALL = True  # Admin can access all clients
LOGO = '/static/img/default-logo.png'
TENANT_CODE = env('TENANT_CODE')
PASSWORD_LENGTH = 16
