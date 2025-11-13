"""
Chat completion endpoint.

This module handles OpenAI-compatible chat completion requests.
"""

import logging
import time
from fastapi import APIRouter, HTTPException

from schemas.chat import ChatCompletionRequest, ChatCompletionResponse
from services.generation_service import format_chat_messages
from api.dependencies import get_model_components, get_function_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["chat"])


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completion(request: ChatCompletionRequest):
    """
    OpenAI-compatible chat completion endpoint.
    
    This endpoint mimics the OpenAI chat completion API format for easier integration
    with existing applications.
    
    Args:
        request: Chat completion request with messages and generation parameters
        
    Returns:
        ChatCompletionResponse: Generated completion in OpenAI format
        
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
        custom_system_prompt = request.system_prompt
        
        # Validate messages
        if not messages or not isinstance(messages, list):
            raise HTTPException(status_code=400, detail="Invalid messages format")
        
        # Format messages with system prompt and function calling instructions
        chat = format_chat_messages(messages, custom_system_prompt, function_registry)
        
        # Validate message format
        for msg in messages:
            if "role" not in msg or "content" not in msg:
                raise HTTPException(status_code=400, detail="Invalid message format")
        
        # Apply chat template
        formatted_prompt = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
        
        # Start timing
        start_time = time.time()
        
        # Tokenize the text
        input_tokens = tokenizer(formatted_prompt, return_tensors="pt").to(device)
        
        # Generate output tokens
        output = model.generate(
            **input_tokens,
            max_new_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=temperature > 0.0
        )
        
        # Decode output tokens into text
        # Extract only the new tokens (exclude the input prompt)
        input_length = input_tokens["input_ids"].shape[1]
        generated_text = tokenizer.batch_decode(output[:, input_length:], skip_special_tokens=True)[0]
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Format response in OpenAI-like structure
        response = {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "ibm-granite/granite-4.0-1b",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": generated_text
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(input_tokens["input_ids"][0]),
                "completion_tokens": len(output[0]) - len(input_tokens["input_ids"][0]),
                "total_tokens": len(output[0])
            }
        }
        
        return response
    
    except Exception as e:
        logger.error(f"Error in chat completion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in chat completion: {str(e)}")


# Made with Bob