import asyncio
import logging

from django.core.handlers.asgi import RequestAborted
from django.db import connections
from django.http import HttpResponse, HttpResponseServerError

LOGGER = logging.getLogger("django")


class IgnoreClientDisconnectsMiddleware:
    """
    Silences normal client disconnects in ASGI (browser navigation away,
    proxy timeout, mobile network drop).

    Prevents RequestAborted / CancelledError from being logged as errors.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        try:
            return await self.app(scope, receive, send)
        except RequestAborted:
            # Client disconnected — expected behavior
            return
        except asyncio.CancelledError:
            # ASGI task cancelled on disconnect
            return


class HealthCheckMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "GET":
            if request.path == "/readyz":
                return self.readiness(request)
            elif request.path == "/livez":
                return self.liveness(request)
        return self.get_response(request)

    def liveness(self, request):
        """Returns that the server is alive."""
        return HttpResponse("OK")

    def readiness(self, request):
        """Connect to each database and do a generic standard SQL query
        that doesn't write any data and doesn't depend on any tables
        being present.
        """
        try:
            cursor = connections["default"].cursor()
            cursor.execute("SELECT 1;")
            row = cursor.fetchone()
            cursor.close()
            if row is None:
                return HttpResponseServerError("Database: invalid response")
        except Exception as e:
            LOGGER.exception(e)
            return HttpResponseServerError("Database: unable to connect")

        return HttpResponse("OK")
