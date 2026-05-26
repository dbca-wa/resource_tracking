import asyncio
import logging

from django.core.handlers.asgi import RequestAborted
from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse

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
            # Propagate task cancellation so lifespan/startup/shutdown and other
            # non-disconnect cancellation paths continue to behave correctly.
            raise


class HealthCheckMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "GET":
            if request.path == "/readyz":
                return self.readiness()
            elif request.path == "/livez":
                return self.liveness()
        return self.get_response(request)

    def liveness(self):
        """Returns that the server is alive."""
        return JsonResponse({"status": "ok"}, status=200)

    def readiness(self):
        """Connect to each database and do a generic standard SQL query
        that doesn't write any data and doesn't depend on any tables
        being present.
        """
        try:
            # Iterate through all configured databases
            for db_name in connections:
                connection = connections[db_name]

                # Ensure connection is established
                connection.ensure_connection()

                # Perform a lightweight query
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1;")
                    cursor.fetchone()

            return JsonResponse({"status": "ok"}, status=200)

        except OperationalError as e:
            return JsonResponse({"status": "error", "detail": str(e)}, status=503)
