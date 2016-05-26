"""
WSGI config for resource_tracking project.
It exposes the WSGI callable as a module-level variable named ``application``.
"""
import confy
confy.read_environment_file('.env')  # Must precede dj_static imports.
from django.core.wsgi import get_wsgi_application
from dj_static import Cling
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "resource_tracking.settings")
application = Cling(get_wsgi_application())
