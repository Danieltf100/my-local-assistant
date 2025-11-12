from docling.document_converter import DocumentConverter
from pathlib import Path
import asyncio
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class DoclingProcessor:
    """Handles document processing with Docling"""
    
    def __init__(self):
        self.converter = DocumentConverter()
        logger.info("DoclingProcessor initialized")
    
    async def process_document(self, file_path: str) -> Dict[str, Any]:
        """
        Process document and extract markdown content.
        Runs in thread pool to avoid blocking.
        """
        try:
            # Run Docling conversion in thread pool (it's CPU-intensive)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._convert_document,
                file_path
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing document {file_path}: {str(e)}")
            return {
                "markdown": "",
                "metadata": {"filename": Path(file_path).name},
                "success": False,
                "error": str(e)
            }
    
    def _convert_document(self, file_path: str) -> Dict[str, Any]:
        """Synchronous document conversion"""
        try:
            logger.info(f"Converting document: {file_path}")
            result = self.converter.convert(file_path)
            markdown_content = result.document.export_to_markdown()
            
            # Extract metadata
            metadata = {
                "filename": Path(file_path).name,
                "page_count": getattr(result.document, 'page_count', None),
                "title": self._extract_title(markdown_content),
                "content_length": len(markdown_content),
                "format": Path(file_path).suffix[1:].upper()
            }
            
            logger.info(f"Document converted successfully: {metadata['filename']} ({metadata['content_length']} chars)")
            
            return {
                "markdown": markdown_content,
                "metadata": metadata,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error in _convert_document: {str(e)}")
            return {
                "markdown": "",
                "metadata": {"filename": Path(file_path).name},
                "success": False,
                "error": str(e)
            }
    
    def _extract_title(self, markdown: str) -> str:
        """Extract title from markdown (first heading or first line)"""
        if not markdown:
            return "Untitled Document"
        
        lines = markdown.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('#'):
                return line.lstrip('#').strip()
            elif line:
                return line[:100]  # First 100 chars
        return "Untitled Document"
    
    async def process_multiple_documents(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """Process multiple documents in parallel"""
        logger.info(f"Processing {len(file_paths)} documents in parallel")
        tasks = [self.process_document(path) for path in file_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions in results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error processing {file_paths[i]}: {str(result)}")
                processed_results.append({
                    "markdown": "",
                    "metadata": {"filename": Path(file_paths[i]).name},
                    "success": False,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
        
        success_count = sum(1 for r in processed_results if r.get("success"))
        logger.info(f"Processed {success_count}/{len(file_paths)} documents successfully")
        
        return processed_results

# Made with Bob
