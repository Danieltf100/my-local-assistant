"""
Streaming endpoint for real-time token generation.

This module handles streaming responses for chat completions.
"""

import logging
import json
from typing import AsyncIterator
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from transformers import TextIteratorStreamer
import torch

from schemas.chat import ChatCompletionRequest
from services.generation_service import (
    _create_stream_id,
    _create_token_chunk,
    _managed_generation_thread,
    _safe_stop_streamer,
    format_chat_messages,
    DISCONNECTION_EXCEPTIONS
)
from api.dependencies import get_model_components, get_function_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["streaming"])


@router.post("/stream")
async def stream_response(request: ChatCompletionRequest):
    """
    Stream response tokens in real-time.
    
    This endpoint accepts chat messages and streams the generated response
    token by token in a format compatible with OpenAI's streaming API.
    
    Args:
        request: Chat completion request with messages and generation parameters
        
    Returns:
        StreamingResponse: JSON stream of generated tokens
        
    Raises:
        HTTPException: For invalid requests or generation errors
    """
    model, tokenizer, device = get_model_components()
    function_registry = get_function_registry()
    
    try:
        # Extract parameters from the request
        messages = request.messages
        max_tokens = request.max_tokens
        temperature = request.temperature
        top_p = request.top_p
        top_k = request.top_k
        do_sample = request.do_sample if request.do_sample is not None else temperature > 0.0
        custom_system_prompt = request.system_prompt
        
        # Validate messages
        if not messages or not isinstance(messages, list):
            raise HTTPException(status_code=400, detail="Invalid messages format")
        
        # Validate message format
        for msg in messages:
            if "role" not in msg or "content" not in msg:
                raise HTTPException(status_code=400, detail="Invalid message format")
        
        # Format messages with system prompt and function calling instructions
        chat = format_chat_messages(messages, custom_system_prompt, function_registry)
        
        # Apply chat template
        formatted_prompt = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
        
        # Tokenize the text
        input_tokens = tokenizer(formatted_prompt, return_tensors="pt").to(device)
        
        # Set up streamer - skip prompt tokens to only stream the generated response
        streamer = TextIteratorStreamer(tokenizer, skip_special_tokens=True, skip_prompt=True)
        
        # Prepare generation parameters
        generation_kwargs = {
            **input_tokens,
            "max_new_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "do_sample": do_sample,
            "streamer": streamer
        }
        
        # Add optional parameters if provided
        if top_k is not None:
            generation_kwargs["top_k"] = top_k
        
        # Define async generator for streaming
        async def token_generator() -> AsyncIterator[str]:
            """
            Async generator that streams tokens from the model.
            
            Yields JSON-formatted chunks containing generated tokens.
            Handles client disconnections and ensures proper cleanup.
            """
            try:
                # Yield opening JSON structure
                yield f'{{"id": "{_create_stream_id()}", "choices": ['
                
                # Use context manager for thread lifecycle management
                with _managed_generation_thread(model.generate, generation_kwargs):
                    # Stream tokens with index tracking
                    for index, token in enumerate(streamer):
                        # Add comma separator between chunks (except first)
                        if index > 0:
                            yield ','
                        yield _create_token_chunk(index, token)
                
                # Yield closing JSON structure
                yield '], "finish_reason": "stop"}'
                
            except DISCONNECTION_EXCEPTIONS as e:
                # Client disconnected - this is expected when user stops generation
                logger.info(f"Client disconnected during streaming: {type(e).__name__}")
                _safe_stop_streamer(streamer)
                
            except Exception as e:
                # Log unexpected errors but don't crash
                logger.error(f"Error during token streaming: {str(e)}")
                _safe_stop_streamer(streamer)
        
        return StreamingResponse(
            token_generator(),
            media_type="application/json",
            headers={
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0',
                'X-Accel-Buffering': 'no'  # Disable buffering for nginx
            }
        )
    
    except torch.cuda.OutOfMemoryError as e:
        logger.error(f"CUDA out of memory error in streaming: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="GPU memory exceeded. Try reducing max_tokens or using a smaller model."
        )
    except ValueError as e:
        logger.error(f"Value error in streaming: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid request parameters: {str(e)}")
    except Exception as e:
        logger.error(f"Error in streaming: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error in streaming: {str(e)}")


# Made with Bob