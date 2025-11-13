"""Services module for the Tiny LLM application."""

from .function_service import FunctionRegistry
from .weather_service import get_weather, geocode_location
from .search_service import search_web
from .document_service import (
    format_document_context,
    prepare_prompt_with_context,
    process_document_with_cache,
)
from .generation_service import (
    create_token_generator,
    prepare_generation_params,
    format_chat_prompt,
    DISCONNECTION_EXCEPTIONS,
    GENERATION_THREAD_TIMEOUT,
)

__all__ = [
    # Function service
    "FunctionRegistry",
    # Weather service
    "get_weather",
    "geocode_location",
    # Search service
    "search_web",
    # Document service
    "format_document_context",
    "prepare_prompt_with_context",
    "process_document_with_cache",
    # Generation service
    "create_token_generator",
    "prepare_generation_params",
    "format_chat_prompt",
    "DISCONNECTION_EXCEPTIONS",
    "GENERATION_THREAD_TIMEOUT",
]

# Made with Bob
