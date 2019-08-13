from dbca_utils.utils import env
import dj_database_url
import os
from pathlib import Path

# Project paths
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = str(Path(__file__).resolve().parents[1])

# Application definition
DEBUG = env('DEBUG', False)
SECRET_KEY = env('SECRET_KEY', 'PlaceholderSecretKey')
CSRF_COOKIE_SECURE = env('CSRF_COOKIE_SECURE', False)
SESSION_COOKIE_SECURE = env('SESSION_COOKIE_SECURE', False)
if not DEBUG:
    ALLOWED_HOSTS = env('ALLOWED_DOMAINS', 'localhost').split(',')
else:
    ALLOWED_HOSTS = ['*']
INTERNAL_IPS = ['127.0.0.1', '::1']
ROOT_URLCONF = 'resource_tracking.urls'
WSGI_APPLICATION = 'resource_tracking.wsgi.application'
CSW_URL = env('CSW_URL', '')
PRINTING_URL = env('PRINTING_URL', '')
TRACPLUS_URL = env('TRACPLUS_URL', False)
KMI_VEHICLE_BASE_URL = env('KMI_VEHICLE_BASE_URL', '')
JQUERY_SOURCE = env('JQUERY_SOURCE', '')
JQUERYUI_SOURCE = env('JQUERYUI_SOURCE', '')
DFES_URL = env('DFES_URL', False)
DFES_USER = env('DFES_USER', False)
DFES_PASS = env('DFES_PASS', False)
DFES_OUT_OF_ORDER_BUFFER = int(env('DFES_OUT_OF_ORDER_BUFFER') or 300)
# Add scary warning on device edit page for prod
PROD_SCARY_WARNING = env('PROD_SCARY_WARNING', False)
DEVICE_HTTP_CACHE_TIMEOUT = env('DEVICE_HTTP_CACHE_TIMEOUT', 60)
HISTORY_HTTP_CACHE_TIMEOUT = env('HISTORY_HTTP_CACHE_TIMEOUT', 60)
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'tastypie',
    'django_extensions',
    'djgeojson',
    # Sub-app definitions
    'tracking',
    'weather',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'dbca_utils.middleware.SSOLoginMiddleware',
]
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

# Email settings
ADMINS = ('asi@dbca.wa.gov.au',)
EMAIL_HOST = env('EMAIL_HOST', 'email.host')
EMAIL_PORT = env('EMAIL_PORT', 25)
EMAIL_USER = env('EMAIL_USER', 'username')
EMAIL_PASSWORD = env('EMAIL_PASSWORD', 'password')


SERIALIZATION_MODULES = {
    "geojson": "djgeojson.serializers",
}


# Database
DATABASES = {
    # Defined in the DATABASE_URL env variable.
    'default': dj_database_url.config(),
}

# Project authentication settings
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Australia/Perth'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')


# Logging settings - log to stdout/stderr
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {'format': '%(asctime)s %(levelname)-8s %(message)s'},
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'console'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'weather': {
            'handlers': ['console'],
            'level': 'INFO'
        },
        'dafwa': {
            'handlers': ['console'],
            'level': 'INFO'
        },
        'dafwa_uploads': {
            'handlers': ['console'],
            'level': 'INFO'
        },
        'tracking_points': {
            'handlers': ['console'],
            'level': 'INFO'
        },
    }
}

JS_MINIFY = False
RESOURCE_FILES_WITH_AUTO_VERSION = [
    os.path.join(BASE_DIR, "tracking", "static", "sss", "sss.js"),
    os.path.join(BASE_DIR, "tracking", "static", "sss", "leaflet.dump.js"),
    os.path.join(BASE_DIR, "tracking", "static", "sss", "sss.css"),
]

# Tastypie settings
TASTYPIE_DEFAULT_FORMATS = ['json']

# DAFWA config
DAFWA_UPLOAD = env('DAFWA_UPLOAD', False)
DAFWA_UPLOAD_HOST = env('DAFWA_UPLOAD_HOST', 'host')
DAFWA_UPLOAD_USER = env('DAFWA_UPLOAD_USER', 'username')
DAFWA_UPLOAD_PASSWORD = env('DAFWA_UPLOAD_PASSWORD', 'password')
DAFWA_UPLOAD_DIR = env('DAFWA_UPLOAD_DIR', '/inbound')

# Sentry configuration
if env('SENTRY_DSN', False):
    SENTRY_CONFIG = {'dsn': env('SENTRY_DSN')}
