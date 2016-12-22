"""
Django settings for resource_tracking project.
"""
from confy import env, database
import os


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Application definition
DEBUG = env('DEBUG', False)
SECRET_KEY = env('SECRET_KEY')
CSRF_COOKIE_SECURE = env('CSRF_COOKIE_SECURE', False)
SESSION_COOKIE_SECURE = env('SESSION_COOKIE_SECURE', False)
if not DEBUG:
    # Localhost, UAT and Production hosts:
    ALLOWED_HOSTS = [
        'localhost',
        '127.0.0.1',
        'resourcetracking.dpaw.wa.gov.au',
        'resourcetracking.dpaw.wa.gov.au.',
        'resourcetracking-uat.dpaw.wa.gov.au',
        'resourcetracking-uat.dpaw.wa.gov.au.',
    ]
else:  # In debug, allow all hosts to serve the application.
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

# add scary warning on device edit page for prod
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
    'django_uwsgi',
    'resource_tracking',
    # Sub-app definitions
    'tracking',
    'weather',
    'djgeojson',
    'dpaw_utils'
]
MIDDLEWARE_CLASSES = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'dpaw_utils.middleware.SSOLoginMiddleware',
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
ADMINS = ('asi@dpaw.wa.gov.au',)
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
    'default': database.config(),
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


# Logging settings
# Ensure that the logs directory exists:
if not os.path.exists(os.path.join(BASE_DIR, 'logs')):
    os.mkdir(os.path.join(BASE_DIR, 'logs'))
LOGGING = {
    'version': 1,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(message)s'
        },
        'minimal': {
            'format': '%(asctime)s %(message)s'
        }
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'resourcetracking.log'),
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 5,
        },
        'weather': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'weather.log'),
            'formatter': 'verbose',
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 5,
        },
        'dafwa': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'dafwa.log'),
            'formatter': 'minimal',
            'maxBytes': 1024 * 1024 * 5,
            'backupCount': 5,
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['file'],
            'level': 'INFO'
        },
        'log': {
            'handlers': ['file'],
            'level': 'INFO'
        },
        'weather': {
            'handlers': ['weather'],
            'level': 'INFO'
        },
        'dafwa': {
            'handlers': ['dafwa'],
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
