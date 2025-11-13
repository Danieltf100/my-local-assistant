"""
API dependencies and shared utilities.

This module provides dependency injection functions for FastAPI routes.
"""

from fastapi import HTTPException
from core import model_manager, get_function_registry, get_file_manager, get_docling_processor, get_cache_manager


def ensure_model_loaded():
    """
    Ensure the model and tokenizer are loaded.
    
    Returns:
        Tuple of (model, tokenizer, device)
        
    Raises:
        HTTPException: If model is not loaded
    """
    if not model_manager.is_loaded():
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Please wait for initialization to complete."
        )
    return model_manager.get_model(), model_manager.get_tokenizer(), model_manager.get_device()


def get_model_components():
    """Get model, tokenizer, and device."""
    return ensure_model_loaded()


def get_function_registry():
    """Get the function registry instance."""
    from core import get_function_registry as _get_registry
    return _get_registry()


def get_file_processing_components():
    """Get file processing components."""
    return get_file_manager(), get_docling_processor(), get_cache_manager()


# Made with Bob
