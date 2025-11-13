"""
Text generation endpoint.

This module provides the text generation API endpoint.
"""

import logging
import torch
from fastapi import APIRouter, HTTPException, BackgroundTasks
from api.dependencies import get_model_components
from schemas import GenerationRequest, GenerationResponse
from services import prepare_generation_params, format_chat_prompt
from core.helpers import Timer

logger = logging.getLogger(__name__)
router = APIRouter(tags=["generation"])


@router.post("/generate", response_model=GenerationResponse)
async def generate_text(request: GenerationRequest, background_tasks: BackgroundTasks):
    """
    Generate text based on the provided prompt and parameters.
    
    This endpoint processes a text generation request with the following steps:
    1. Formats the prompt as a chat message
    2. Applies the model's chat template
    3. Tokenizes the formatted prompt
    4. Generates text using the specified parameters
    5. Returns the generated text with metadata
    
    Args:
        request: The generation request containing prompt and parameters
        background_tasks: FastAPI background tasks manager
        
    Returns:
        GenerationResponse: The generated text and metadata
        
    Raises:
        HTTPException: If an error occurs during text generation
    """
    # Get model components
    model, tokenizer, device = get_model_components()
    
    try:
        # Use the Timer context manager for accurate timing
        with Timer() as timer:
            # Format the prompt as a chat
            chat = format_chat_prompt(request.prompt)
            
            # Apply chat template
            formatted_prompt = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
            
            # Tokenize the text
            input_tokens = tokenizer(formatted_prompt, return_tensors="pt").to(device)
            
            # Prepare generation parameters
            generation_params = prepare_generation_params(
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                do_sample=request.do_sample,
                top_k=request.top_k,
                repetition_penalty=request.repetition_penalty,
                num_return_sequences=request.num_return_sequences
            )
            
            # Generate output tokens
            output = model.generate(**input_tokens, **generation_params)
            
            # Decode output tokens into text
            # Extract only the new tokens (exclude the input prompt)
            input_length = input_tokens["input_ids"].shape[1]
            generated_texts = tokenizer.batch_decode(output[:, input_length:], skip_special_tokens=True)
        
        # Log completion
        logger.info(f"Text generation completed in {timer.elapsed:.2f} seconds")
        
        # Return the first generated text
        return GenerationResponse(
            generated_text=generated_texts[0],
            execution_time=timer.elapsed,
            prompt=request.prompt,
            parameters={field: getattr(request, field) for field in [
                "max_tokens", "temperature", "top_p", "top_k",
                "repetition_penalty", "do_sample", "num_return_sequences"
            ]}
        )
    
    except torch.cuda.OutOfMemoryError as e:
        logger.error(f"CUDA out of memory error: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="GPU memory exceeded. Try reducing max_tokens or using a smaller model."
        )
    except ValueError as e:
        logger.error(f"Value error in text generation: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid request parameters: {str(e)}")
    except Exception as e:
        logger.error(f"Error generating text: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating text: {str(e)}")

# Made with Bob
