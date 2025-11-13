"""
Pydantic schemas for function calling endpoints.

This module contains request and response models for function calling APIs.
"""

from pydantic import BaseModel
from typing import Dict, Any, List, Optional


class FunctionDefinition(BaseModel):
    """Definition of a callable function."""
    
    name: str
    description: str
    parameters: Dict[str, Any]


class FunctionCallRequest(BaseModel):
    """Request model for function calling."""
    
    messages: List[Dict[str, Any]]
    tools: Optional[List[Dict[str, Any]]] = None
    max_tokens: int = 100
    temperature: float = 1.0


class FunctionCallChoice(BaseModel):
    """A single function call choice."""
    
    index: int
    message: Dict[str, str]


class FunctionCallResponse(BaseModel):
    """Response model for function calling."""
    
    id: str
    object: str = "function.call"
    created: int
    model: str
    choices: List[FunctionCallChoice]


class FunctionExecutionRequest(BaseModel):
    """Request model for executing a function."""
    
    function_name: str
    arguments: Dict[str, Any] = {}


class FunctionExecutionResponse(BaseModel):
    """Response model for function execution."""
    
    success: bool
    function_name: str
    result: Optional[Any] = None
    error: Optional[str] = None


class FunctionsListResponse(BaseModel):
    """Response model for listing available functions."""
    
    functions: List[Dict[str, Any]]
    tools: List[Dict[str, Any]]

# Made with Bob
