"""Request ID middleware for tracking requests through logs and distributed tracing."""

import uuid
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add a unique request ID to each request for tracing and debugging.
    
    The request ID is:
    - Generated if not provided in headers
    - Added to the response headers
    - Available in request.state for use in handlers
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add request ID tracking.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware/handler in the chain
            
        Returns:
            The HTTP response with request ID header
        """
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response
