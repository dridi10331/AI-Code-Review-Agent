"""Global exception handlers for the API."""

import logging
from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

logger = logging.getLogger(__name__)


async def pydantic_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle Pydantic validation errors with detailed feedback.
    
    Args:
        request: The HTTP request
        exc: The validation error
        
    Returns:
        JSON response with detailed error information
    """
    errors = [
        {
            "field": ".".join(str(x) for x in error["loc"][1:] if x != "__root__"),
            "message": error["msg"],
            "type": error["type"],
        }
        for error in exc.errors()
    ]
    
    logger.warning(f"Validation error on {request.url.path}: {errors}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Request validation failed",
            "errors": errors,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions with safe error messages.
    
    Args:
        request: The HTTP request
        exc: The exception
        
    Returns:
        JSON response with safe error message
    """
    logger.exception(f"Unhandled exception on {request.url.path}: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle ValueError exceptions.
    
    Args:
        request: The HTTP request
        exc: The value error
        
    Returns:
        JSON response with error message
    """
    logger.warning(f"Value error on {request.url.path}: {exc}")
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )
