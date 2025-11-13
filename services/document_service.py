"""
Document processing service.

This module handles document processing with caching support.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


def format_document_context(processed_files: List[Dict[str, Any]]) -> str:
    """
    Format processed documents as context for LLM.
    
    Args:
        processed_files: List of processed file data dictionaries
        
    Returns:
        Formatted string containing all document content
    """
    if not processed_files:
        return ""
    
    context_parts = ["=== ATTACHED DOCUMENTS ===\n"]
    
    for i, file_data in enumerate(processed_files, 1):
        metadata = file_data.get("metadata", {})
        markdown = file_data.get("markdown", "")
        
        context_parts.append(f"\n--- Document {i}: {metadata.get('filename', 'Unknown')} ---")
        context_parts.append(f"Format: {metadata.get('format', 'Unknown')}")
        
        if metadata.get('page_count'):
            context_parts.append(f"Pages: {metadata['page_count']}")
        
        context_parts.append(f"\nContent:\n{markdown}\n")
        context_parts.append("--- End of Document ---\n")
    
    context_parts.append("\n=== END OF DOCUMENTS ===\n")
    
    return "\n".join(context_parts)


def prepare_prompt_with_context(
    user_prompt: str,
    processed_files: List[Dict[str, Any]],
    system_prompt: Optional[str] = None
) -> str:
    """
    Build enhanced prompt with document context.
    
    Args:
        user_prompt: The user's question or prompt
        processed_files: List of processed documents
        system_prompt: Optional custom system prompt
        
    Returns:
        Enhanced prompt with document context
    """
    # Format document context
    doc_context = format_document_context(processed_files)
    
    # Build instruction for the model
    instruction = """You have been provided with document(s) as reference material.
Please analyze the documents and answer the user's question based on the information provided.
If the answer cannot be found in the documents, please state that clearly."""
    
    # Combine all parts
    if doc_context:
        enhanced_prompt = f"""{instruction}

{doc_context}

User Question: {user_prompt}

Please provide a detailed answer based on the documents above."""
    else:
        enhanced_prompt = user_prompt
    
    return enhanced_prompt


async def process_document_with_cache(
    file_path: str,
    cache_manager,
    docling_processor
) -> Dict[str, Any]:
    """
    Process document with caching support.
    
    Args:
        file_path: Path to the document file
        cache_manager: CacheManager instance
        docling_processor: DoclingProcessor instance
        
    Returns:
        Processed document data
    """
    # Check cache first
    cached = cache_manager.get(file_path)
    if cached:
        logger.info(f"Cache hit for {file_path}")
        return cached
    
    # Process document
    logger.info(f"Cache miss for {file_path}, processing...")
    result = await docling_processor.process_document(file_path)
    
    # Cache result
    if result.get("success"):
        cache_manager.set(file_path, result)
    
    return result

# Made with Bob
