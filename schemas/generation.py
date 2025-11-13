"""
Pydantic schemas for text generation endpoints.

This module contains request and response models for the text generation API.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class GenerationRequest(BaseModel):
    """Request model for text generation."""
    
    prompt: str = Field(..., description="The text prompt to generate from")
    max_tokens: int = Field(100, description="Maximum number of tokens to generate", ge=1, le=1000)
    temperature: float = Field(1.0, description="Sampling temperature", ge=0.0, le=2.0)
    top_p: float = Field(1.0, description="Nucleus sampling parameter", ge=0.0, le=1.0)
    top_k: Optional[int] = Field(None, description="Top-k sampling parameter", ge=0)
    repetition_penalty: Optional[float] = Field(None, description="Repetition penalty", ge=0.0)
    do_sample: bool = Field(True, description="Whether to use sampling or greedy decoding")
    num_return_sequences: Optional[int] = Field(1, description="Number of sequences to return", ge=1, le=5)
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Do you know who you are?",
                "max_tokens": 100,
                "temperature": 0.7,
                "top_p": 0.9,
                "do_sample": True,
                "num_return_sequences": 1
            }
        }


class GenerationResponse(BaseModel):
    """Response model for text generation."""
    
    generated_text: str
    execution_time: float
    model_name: str = "ibm-granite/granite-4.0-1b"
    prompt: str
    parameters: Dict[str, Any]

# Made with Bob
