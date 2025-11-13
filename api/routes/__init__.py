"""
API routes module.

This module aggregates all API routers into a single router.
"""

from fastapi import APIRouter
from .health import router as health_router
from .generation import router as generation_router
from .frontend import router as frontend_router
from .streaming import router as streaming_router
from .chat import router as chat_router
from .functions import router as functions_router
from .files import router as files_router

# Create main router
router = APIRouter()

# Include all sub-routers
router.include_router(health_router)
router.include_router(generation_router)
router.include_router(streaming_router)
router.include_router(chat_router)
router.include_router(functions_router)
router.include_router(files_router)
router.include_router(frontend_router)

__all__ = ["router"]

# Made with Bob
