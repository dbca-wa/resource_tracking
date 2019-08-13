"""
WSGI config for resource_tracking project.
It exposes the WSGI callable as a module-level variable named ``application``.
"""
import dotenv
from django.core.wsgi import get_wsgi_application
import os
from pathlib import Path

# These lines are required for interoperability between local and container environments.
d = Path(__file__).resolve().parents[1]
dot_env = os.path.join(str(d), '.env')
if os.path.exists(dot_env):
    dotenv.read_dotenv(dot_env)  # Must precede dj_static imports.


from dj_static import Cling

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "resource_tracking.settings")
application = Cling(get_wsgi_application())
