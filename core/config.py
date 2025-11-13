"""
Configuration management for the Tiny LLM application.

This module centralizes all configuration settings, environment variables,
and application constants.
"""

import os
from typing import List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application settings and configuration."""
    
    # Model Configuration
    MODEL_PATH: str = "ibm-granite/granite-4.0-1b"
    MODEL_NAME: str = "ibm-granite/granite-4.0-1b"
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True
    
    # API Configuration
    API_TITLE: str = "Granite4Nano-1B API"
    API_DESCRIPTION: str = "API for text generation using the IBM Granite 4.0 1B model"
    API_VERSION: str = "1.0.0"
    
    # File Processing Configuration
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    CACHE_DIR: str = os.getenv("CACHE_DIR", "./cache")
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    CACHE_TTL_HOURS: int = int(os.getenv("CACHE_TTL_HOURS", "24"))
    ALLOWED_EXTENSIONS: List[str] = os.getenv(
        "ALLOWED_EXTENSIONS",
        "pdf,docx,pptx,xlsx,png,jpg,jpeg,gif,txt,md"
    ).split(",")
    
    # External API Configuration
    METEOBLUE_API_KEY: str = os.getenv("METEOBLUE_API_KEY", "demo")
    
    # Generation Defaults
    DEFAULT_MAX_TOKENS: int = 100
    DEFAULT_TEMPERATURE: float = 1.0
    DEFAULT_TOP_P: float = 1.0
    DEFAULT_DO_SAMPLE: bool = True
    
    # Streaming Configuration
    GENERATION_THREAD_TIMEOUT: float = 1.0
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = ["*"]
    CORS_CREDENTIALS: bool = True
    CORS_METHODS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]


# Create a global settings instance
settings = Settings()

# Made with Bob
