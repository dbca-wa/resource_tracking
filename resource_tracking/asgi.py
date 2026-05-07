"""
ASGI config for resource_tracking project.
It exposes the ASGI callable as a module-level variable named ``application``.
"""

import os
from pathlib import Path

from django.core.asgi import get_asgi_application

from resource_tracking.middleware import IgnoreClientDisconnectsMiddleware

# These lines are required for interoperability between local and container environments.
d = Path(__file__).resolve().parent.parent
dot_env = os.path.join(str(d), ".env")
if os.path.exists(dot_env):
    from dotenv import load_dotenv

    load_dotenv()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "resource_tracking.settings")
application = IgnoreClientDisconnectsMiddleware(get_asgi_application())
