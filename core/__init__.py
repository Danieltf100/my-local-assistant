"""Core module for the Tiny LLM application."""

from .config import settings, Settings
from .model_manager import model_manager, ModelManager
from .lifespan import (
    lifespan,
    get_function_registry,
    get_file_manager,
    get_docling_processor,
    get_cache_manager,
)

__all__ = [
    # Config
    "settings",
    "Settings",
    # Model Manager
    "model_manager",
    "ModelManager",
    # Lifespan
    "lifespan",
    "get_function_registry",
    "get_file_manager",
    "get_docling_processor",
    "get_cache_manager",
]

# Made with Bob
