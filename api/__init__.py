"""API module for the Tiny LLM application."""

from .routes import router
from .dependencies import (
    ensure_model_loaded,
    get_model_components,
    get_function_registry,
    get_file_processing_components,
)

__all__ = [
    "router",
    "ensure_model_loaded",
    "get_model_components",
    "get_function_registry",
    "get_file_processing_components",
]

# Made with Bob
