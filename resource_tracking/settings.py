"""
Django settings for resource_tracking project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import dj_database_url
import logging

class Env(object):
    """
    A utility class to read value from environment.
    """
    @staticmethod
    def get_int(key,default):
        """
        Read a int from environmenent 
        """
        try:
            return int(os.environ.get(key,default))
        except:
            return default

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# define the following in the environment
SECRET_KEY = os.environ.get('SECRET_KEY', '')
DEBUG = os.environ.get('DEBUG','False').lower() in ["true","yes","on","t","y"]
GEOSERVER_URL = os.environ.get('GEOSERVER_URL', False)
TRACPLUS_URL = os.environ.get('TRACPLUS_URL', False)
for key in os.environ:
    if key.startswith("EMAIL_"):
        globals()[key] = os.environ[key]

TEMPLATE_DEBUG = True

DEVICE_HTTP_CACHE_TIMEOUT = Env.get_int('DEVICE_HTTP_CACHE_TIMEOUT', 60)
HISTORY_HTTP_CACHE_TIMEOUT = Env.get_int('HISTORY_HTTP_CACHE_TIMEOUT', 60)

ALLOWED_HOSTS = [
    '*'
]

# Application definition

INSTALLED_APPS = (
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
    #'django_wsgiserver',
    'resource_autoversion',
    'resource_tracking',
    # Sub-app definitions
    'tracking',
    'djgeojson',
    'dpaw_utils'
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'dpaw_utils.middleware.SSOLoginMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

SERIALIZATION_MODULES = {
    "geojson": "djgeojson.serializers", 
 }

ROOT_URLCONF = 'resource_tracking.urls'
WSGI_APPLICATION = 'resource_tracking.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases
DATABASES = {'default': dj_database_url.config()}

# Project authentication settings
#from ldap_email_auth import ldap_default_settings
#ldap_default_settings()
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    #'ldap_email_auth.auth.EmailBackend',
)

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Australia/Perth'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')


logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s %(levelname)s %(message)s',
)

JS_MINIFY = False
RESOURCE_FILES_WITH_AUTO_VERSION = [
    os.path.join(BASE_DIR,"tracking","static","sss","sss.js"),
    os.path.join(BASE_DIR,"tracking","static","sss","jquery.print.js"),
    os.path.join(BASE_DIR,"tracking","static","sss","sss.css"),
    os.path.join(BASE_DIR,"tracking","static","sss","sss.print.css"),
]
