"""
Pydantic schemas for chat completion endpoints.

This module contains request and response models for chat-related APIs.
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class ChatMessage(BaseModel):
    """A single chat message."""
    
    role: str
    content: str
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    """Request model for chat completion."""
    
    messages: List[Dict[str, Any]]
    max_tokens: int = 100
    temperature: float = 1.0
    top_p: float = 1.0
    top_k: Optional[int] = None
    do_sample: Optional[bool] = None
    system_prompt: Optional[str] = None
    stream: bool = False


class ChatCompletionChoice(BaseModel):
    """A single completion choice."""
    
    index: int
    message: Dict[str, str]
    finish_reason: str


class ChatCompletionUsage(BaseModel):
    """Token usage information."""
    
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """Response model for chat completion."""
    
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: ChatCompletionUsage


class FileUploadChatRequest(BaseModel):
    """Request model for chat with file uploads."""
    
    prompt: str
    max_tokens: int = 100
    temperature: float = 0.7
    top_p: float = 0.9
    system_prompt: Optional[str] = None


class FileUploadChatResponse(BaseModel):
    """Response model for chat with file uploads."""
    
    response: str
    files_processed: List[Dict[str, Any]]
    execution_time: float

# Made with Bob
