"""
Function calling endpoints.

This module handles function calling capabilities and function execution.
"""

import logging
import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from schemas.functions import FunctionCallRequest, FunctionExecutionRequest
from api.dependencies import get_model_components, get_function_registry

logger = logging.getLogger(__name__)

router = APIRouter(tags=["functions"])


@router.post("/v1/function_call")
async def function_call(request: FunctionCallRequest):
    """
    Endpoint for function calling capabilities.
    
    This endpoint allows the model to use tools/functions defined in the request.
    
    Args:
        request: Function call request with messages, tools, and generation parameters
        
    Returns:
        Generated response with function call information
        
    Raises:
        HTTPException: For invalid requests or generation errors
    """
    model, tokenizer, device = get_model_components()
    
    try:
        # Extract parameters from the request
        messages = request.messages
        tools = request.tools
        max_tokens = request.max_tokens
        temperature = request.temperature
        
        # Validate messages
        if not messages or not isinstance(messages, list):
            raise HTTPException(status_code=400, detail="Invalid messages format")
        
        # Format messages for our model
        chat = []
        for msg in messages:
            if "role" not in msg or "content" not in msg:
                raise HTTPException(status_code=400, detail="Invalid message format")
            chat.append({"role": msg["role"], "content": msg["content"]})
        
        # Apply chat template with tools
        formatted_prompt = tokenizer.apply_chat_template(
            chat, 
            tokenize=False, 
            add_generation_prompt=True,
            tools=tools
        )
        
        # Tokenize the text
        input_tokens = tokenizer(formatted_prompt, return_tensors="pt").to(device)
        
        # Generate output tokens
        output = model.generate(
            **input_tokens,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=temperature > 0.0
        )
        
        # Decode output tokens into text
        # Extract only the new tokens (exclude the input prompt)
        input_length = input_tokens["input_ids"].shape[1]
        generated_text = tokenizer.batch_decode(output[:, input_length:], skip_special_tokens=True)[0]
        
        # Format response
        response = {
            "id": f"funcall-{int(time.time())}",
            "object": "function.call",
            "created": int(time.time()),
            "model": "ibm-granite/granite-4.0-1b",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": generated_text
                    }
                }
            ]
        }
        
        return response
    
    except Exception as e:
        logger.error(f"Error in function call: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error in function call: {str(e)}")


@router.get("/api/functions")
async def get_available_functions():
    """
    Get list of all available functions that can be called.
    
    Returns:
        JSONResponse: Dictionary containing available functions and tools schema
    """
    function_registry = get_function_registry()
    
    return JSONResponse(content={
        "functions": function_registry.get_all_functions(),
        "tools": function_registry.get_tools_schema()
    })


@router.post("/api/execute_function")
async def execute_function(request: FunctionExecutionRequest):
    """
    Execute a registered function with given arguments.
    
    Args:
        request: Function execution request with function name and arguments
        
    Returns:
        JSONResponse: Execution result or error
        
    Raises:
        HTTPException: For invalid requests or execution errors
    """
    function_registry = get_function_registry()
    
    try:
        function_name = request.function_name
        arguments = request.arguments
        
        if not function_name:
            raise HTTPException(status_code=400, detail="function_name is required")
        
        logger.info(f"Executing function: {function_name} with arguments: {arguments}")
        
        # Execute the function (await since it's async now)
        result = await function_registry.execute(function_name, arguments)
        
        if not result["success"]:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": result["error"]}
            )
        
        return JSONResponse(content={
            "success": True,
            "function_name": function_name,
            "result": result["result"]
        })
        
    except Exception as e:
        logger.error(f"Error executing function: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Made with Bob