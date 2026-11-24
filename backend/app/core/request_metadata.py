"""Request correlation, bounded URL queries, and logs without query values."""

import logging
from time import perf_counter
from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)
MAX_QUERY_BYTES = 4096


class RequestMetadataMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        start = perf_counter()
        status = 500

        async def send_response(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        try:
            if len(scope["query_string"]) > MAX_QUERY_BYTES:
                await JSONResponse({"detail": "Query string too large"}, status_code=414)(scope, receive, send_response)
            else:
                await self.app(scope, receive, send_response)
        finally:
            route = getattr(scope.get("route"), "path", "<unmatched>")
            logger.info("request_id=%s method=%s route=%s status=%d duration_ms=%.1f",
                        request_id, scope["method"], route, status, (perf_counter() - start) * 1000)
