"""
Health check endpoint.

This module provides a simple health check endpoint to verify the API is running.
"""

from fastapi import APIRouter, HTTPException
from api.dependencies import ensure_model_loaded
from core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """
    Check if the API and model are ready.
    
    Returns:
        dict: Status information including model name
        
    Raises:
        HTTPException: If model is not loaded
    """
    try:
        ensure_model_loaded()
        return {
            "status": "ok",
            "model": settings.MODEL_NAME
        }
    except HTTPException:
        raise HTTPException(status_code=503, detail="Model not loaded")

# Made with Bob
