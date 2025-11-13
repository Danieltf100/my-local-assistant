"""
Application lifespan management.

This module handles startup and shutdown events for the FastAPI application.
"""

import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .model_manager import model_manager
from .config import settings
from services import FunctionRegistry, get_weather, search_web
from utils import FileManager, DoclingProcessor, CacheManager, CleanupScheduler

logger = logging.getLogger(__name__)

# Global instances
function_registry = FunctionRegistry()
file_manager = None
docling_processor = None
cache_manager = None
cleanup_scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    
    Args:
        app: FastAPI application instance
    """
    global file_manager, docling_processor, cache_manager, cleanup_scheduler
    
    # Startup
    try:
        # Load model and tokenizer
        model_manager.load_model()
        
        # Initialize file processing components
        logger.info("Initializing file processing system...")
        
        file_manager = FileManager(
            upload_dir=settings.UPLOAD_DIR,
            max_size_mb=settings.MAX_FILE_SIZE_MB,
            allowed_extensions=settings.ALLOWED_EXTENSIONS
        )
        
        docling_processor = DoclingProcessor()
        
        cache_manager = CacheManager(
            cache_dir=settings.CACHE_DIR,
            ttl_hours=settings.CACHE_TTL_HOURS
        )
        
        # Start cleanup scheduler
        cleanup_scheduler = CleanupScheduler(file_manager, cache_manager)
        cleanup_scheduler.start()
        
        logger.info("File processing system initialized")
        
        # Register functions
        logger.info("Registering functions...")
        
        # Register weather function
        function_registry.register(
            name="get_weather",
            description="Get current weather information for a specific location",
            parameters={
                "location": {
                    "type": "string",
                    "description": "The city or location name",
                    "required": True
                },
                "units": {
                    "type": "string",
                    "description": "Temperature units (celsius or fahrenheit)",
                    "enum": ["celsius", "fahrenheit"],
                    "required": False
                }
            },
            handler=get_weather
        )
        
        # Register web search function
        function_registry.register(
            name="search_web",
            description="Search the web for information using DuckDuckGo. Returns abstracts, related topics, and sources. Use this when you need current information, facts, or details about any topic.",
            parameters={
                "query": {
                    "type": "string",
                    "description": "The search query or question",
                    "required": True
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of related topics to return (default: 5)",
                    "required": False
                }
            },
            handler=search_web
        )
        
        logger.info(f"Registered {len(function_registry.functions)} functions")
        
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise e
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    if cleanup_scheduler:
        cleanup_scheduler.shutdown()


def get_function_registry() -> FunctionRegistry:
    """Get the global function registry instance."""
    return function_registry


def get_file_manager():
    """Get the global file manager instance."""
    return file_manager


def get_docling_processor():
    """Get the global docling processor instance."""
    return docling_processor


def get_cache_manager():
    """Get the global cache manager instance."""
    return cache_manager

# Made with Bob
