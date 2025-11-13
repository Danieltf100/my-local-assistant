"""
File upload endpoint for chat with documents.

This module handles file uploads and document processing for chat.
"""

import logging
import time
from typing import List, Optional
from fastapi import APIRouter, HTTPException, File, Form, UploadFile
from fastapi.responses import JSONResponse

from services.document_service import prepare_prompt_with_context, process_document_with_cache
from api.dependencies import get_model_components, get_file_processing_components

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["files"])


@router.post("/chat/upload")
async def chat_with_files(
    prompt: str = Form(...),
    files: List[UploadFile] = File(None),
    max_tokens: int = Form(100),
    temperature: float = Form(0.7),
    top_p: float = Form(0.9),
    system_prompt: Optional[str] = Form(None)
):
    """
    Chat endpoint that accepts text prompt and optional file attachments.
    Processes files with Docling and includes content as context.
    
    Args:
        prompt: User's text prompt/question
        files: Optional list of uploaded files
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature
        top_p: Nucleus sampling parameter
        system_prompt: Optional custom system prompt
        
    Returns:
        JSONResponse: Generated response with file processing information
        
    Raises:
        HTTPException: For invalid requests or processing errors
    """
    model, tokenizer, device = get_model_components()
    file_manager, docling_processor, cache_manager = get_file_processing_components()
    
    try:
        start_time = time.time()
        processed_files = []
        
        # Process files if provided
        if files and len(files) > 0:
            logger.info(f"Processing {len(files)} uploaded files")
            
            for file in files:
                # Read file content
                content = await file.read()
                
                # Validate file
                is_valid, error_msg = file_manager.validate_file(file.filename, len(content))
                if not is_valid:
                    raise HTTPException(status_code=400, detail=error_msg)
                
                # Save file
                file_path = await file_manager.save_file(content, file.filename)
                
                # Process with Docling (with caching)
                processed_content = await process_document_with_cache(
                    file_path,
                    cache_manager,
                    docling_processor
                )
                
                if processed_content.get("success"):
                    processed_files.append(processed_content)
                else:
                    logger.warning(f"Failed to process {file.filename}: {processed_content.get('error')}")
        
        # Prepare enhanced prompt with document context
        if processed_files:
            enhanced_prompt = prepare_prompt_with_context(prompt, processed_files, system_prompt)
        else:
            enhanced_prompt = prompt
        
        # Format messages for chat completion
        messages = [{"role": "user", "content": enhanced_prompt}]
        
        # Add custom system prompt if provided and no files
        if system_prompt and not processed_files:
            messages.insert(0, {"role": "system", "content": system_prompt})
        
        # Format chat
        chat = []
        for msg in messages:
            chat.append({"role": msg["role"], "content": msg["content"]})
        
        # Apply chat template
        formatted_prompt = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
        
        # Tokenize
        input_tokens = tokenizer(formatted_prompt, return_tensors="pt").to(device)
        
        # Generate
        output = model.generate(
            **input_tokens,
            max_new_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=temperature > 0.0
        )
        
        # Decode
        input_length = input_tokens["input_ids"].shape[1]
        generated_text = tokenizer.batch_decode(output[:, input_length:], skip_special_tokens=True)[0]
        
        execution_time = time.time() - start_time
        
        # Format response
        response = {
            "response": generated_text,
            "files_processed": [
                {
                    "filename": f.get("metadata", {}).get("filename", "Unknown"),
                    "pages": f.get("metadata", {}).get("page_count"),
                    "status": "success" if f.get("success") else "failed"
                }
                for f in processed_files
            ],
            "execution_time": execution_time
        }
        
        logger.info(f"Chat with files completed in {execution_time:.2f}s, processed {len(processed_files)} files")
        
        return JSONResponse(content=response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat_with_files: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


# Made with Bob