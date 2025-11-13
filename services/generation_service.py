"""
Text generation service.

This module handles text generation logic including streaming support.
"""

import logging
import time
import json
from typing import Dict, Any, AsyncIterator, Callable, Optional
from contextlib import contextmanager
from threading import Thread
from transformers import TextIteratorStreamer

logger = logging.getLogger(__name__)

# Constants for exception handling
DISCONNECTION_EXCEPTIONS = (
    ConnectionResetError,
    ConnectionAbortedError,
    BrokenPipeError,
    GeneratorExit
)

# Thread management timeout (seconds)
GENERATION_THREAD_TIMEOUT = 1.0


def _create_stream_id() -> str:
    """
    Generate a unique stream ID based on current timestamp.
    
    Returns:
        str: Unique stream identifier in format 'stream-{timestamp}'
    """
    return f"stream-{int(time.time())}"


def _create_token_chunk(index: int, content: str, finish_reason: Optional[str] = None) -> str:
    """
    Create a JSON-formatted chunk for a single token.
    
    Args:
        index: Token index in the stream
        content: Token content/text
        finish_reason: Optional finish reason (e.g., 'stop', 'length')
    
    Returns:
        str: JSON-formatted chunk string
    """
    chunk = {
        "index": index,
        "delta": {"content": content},
        "finish_reason": finish_reason
    }
    return json.dumps(chunk)


def _safe_stop_streamer(streamer: TextIteratorStreamer) -> None:
    """
    Safely stop the streamer if it has an end method.
    
    Args:
        streamer: TextIteratorStreamer instance to stop
    """
    if hasattr(streamer, 'end'):
        try:
            streamer.end()
        except Exception as e:
            logger.debug(f"Error stopping streamer: {e}")


@contextmanager
def _managed_generation_thread(
    target: Callable,
    kwargs: Dict[str, Any],
    timeout: float = GENERATION_THREAD_TIMEOUT
):
    """
    Context manager for generation thread lifecycle management.
    
    Ensures the thread is properly started and cleaned up, even if exceptions occur.
    
    Args:
        target: Function to run in the thread
        kwargs: Keyword arguments for the target function
        timeout: Maximum time to wait for thread completion (seconds)
    
    Yields:
        Thread: The started generation thread
    """
    thread = Thread(target=target, kwargs=kwargs)
    thread.start()
    try:
        yield thread
    finally:
        if thread.is_alive():
            thread.join(timeout=timeout)


async def create_token_generator(
    model,
    streamer: TextIteratorStreamer,
    generation_kwargs: Dict[str, Any]
) -> AsyncIterator[str]:
    """
    Create an async generator that streams tokens from the model.
    
    Args:
        model: The language model
        streamer: TextIteratorStreamer instance
        generation_kwargs: Generation parameters
        
    Yields:
        JSON-formatted chunks containing generated tokens
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


def prepare_generation_params(
    max_tokens: int,
    temperature: float,
    top_p: float,
    do_sample: bool,
    top_k: Optional[int] = None,
    repetition_penalty: Optional[float] = None,
    num_return_sequences: Optional[int] = None
) -> Dict[str, Any]:
    """
    Prepare generation parameters from request values.
    
    Args:
        max_tokens: Maximum number of tokens to generate
        temperature: Sampling temperature
        top_p: Nucleus sampling parameter
        do_sample: Whether to use sampling
        top_k: Optional top-k sampling parameter
        repetition_penalty: Optional repetition penalty
        num_return_sequences: Optional number of sequences to return
        
    Returns:
        Dictionary of generation parameters
    """
    params = {
        "max_new_tokens": max_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "do_sample": do_sample,
    }
    
    if num_return_sequences is not None:
        params["num_return_sequences"] = num_return_sequences
    else:
        params["num_return_sequences"] = 1
        
    if top_k is not None:
        params["top_k"] = top_k
    if repetition_penalty is not None:
        params["repetition_penalty"] = repetition_penalty
        
    return params


def format_chat_prompt(prompt: str) -> list:
    """
    Format a text prompt as a chat message.
    
    Args:
        prompt: The text prompt
        
    Returns:
        List containing the formatted chat message
    """
    return [{"role": "user", "content": prompt}]


def format_chat_messages(
    messages: list,
    custom_system_prompt: Optional[str],
    function_registry
) -> list:
    """
    Format chat messages with system prompt and function calling instructions.
    
    Args:
        messages: List of chat messages from the request
        custom_system_prompt: Optional custom system prompt
        function_registry: Function registry instance for available functions
        
    Returns:
        List of formatted chat messages
    """
    from datetime import datetime
    
    chat = []
    
    # Add system message
    if custom_system_prompt:
        # Use custom system prompt if provided
        chat.append({"role": "system", "content": custom_system_prompt})
    else:
        # Use default system message with function calling instructions
        available_functions = function_registry.get_all_functions()
        if available_functions:
            functions_desc = "\n".join([
                f"- {func['name']}: {func['description']}\n  Parameters: {json.dumps(func['parameters'])}"
                for func in available_functions
            ])
            
            # Get current date and time
            current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            system_message = f"""You are a helpful assistant with access to the following functions:

{functions_desc}

Current date and time: {current_datetime}

When you need to use a function, respond with:
<function_call>
{{"name": "function_name", "arguments": {{"param1": "value1", "param2": "value2"}}}}
</function_call>

You can include reasoning text before the function call to explain what you're doing.
After the function executes, you'll receive the result and can continue the conversation."""
            
            chat.append({"role": "system", "content": system_message})
    
    # Add user messages and handle function results
    for msg in messages:
        # Convert function role to user role with special formatting
        if msg["role"] == "function":
            function_name = msg.get("name", "unknown_function")
            function_content = msg["content"]
            # Format function result as a user message so the model can process it
            chat.append({
                "role": "user",
                "content": f"Function '{function_name}' returned:\n{function_content}"
            })
        else:
            chat.append({"role": msg["role"], "content": msg["content"]})
    
    return chat


# Made with Bob
