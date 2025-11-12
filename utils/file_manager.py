import os
import hashlib
import aiofiles
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)

class FileManager:
    """Manages file storage, validation, and cleanup"""
    
    def __init__(self, upload_dir: str, max_size_mb: int, allowed_extensions: List[str]):
        self.upload_dir = Path(upload_dir)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.allowed_extensions = set(ext.lower() for ext in allowed_extensions)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"FileManager initialized: {self.upload_dir}, max_size={max_size_mb}MB")
    
    def validate_file(self, filename: str, file_size: int) -> Tuple[bool, Optional[str]]:
        """Validate file extension and size"""
        # Check size
        if file_size > self.max_size_bytes:
            return False, f"File size exceeds {self.max_size_bytes / (1024*1024):.0f}MB limit"
        
        # Check extension
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext not in self.allowed_extensions:
            return False, f"File type .{ext} not supported"
        
        return True, None
    
    async def save_file(self, file_content: bytes, filename: str) -> str:
        """Save file with unique name and return file path"""
        # Generate unique filename using hash + timestamp
        file_hash = hashlib.md5(file_content).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = filename.rsplit('.', 1)[-1] if '.' in filename else 'bin'
        
        # Sanitize original filename
        safe_filename = self._sanitize_filename(filename)
        unique_filename = f"{timestamp}_{file_hash}_{safe_filename}"
        
        file_path = self.upload_dir / unique_filename
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)
        
        logger.info(f"File saved: {unique_filename} ({len(file_content)} bytes)")
        return str(file_path)
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent path traversal"""
        import re
        # Remove path components
        filename = Path(filename).name
        # Remove dangerous characters, keep alphanumeric, spaces, dots, hyphens, underscores
        filename = re.sub(r'[^\w\s\-\.]', '', filename)
        # Limit length
        if len(filename) > 200:
            name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            filename = name[:195] + ('.' + ext if ext else '')
        return filename
    
    def cleanup_old_files(self, max_age_hours: int = 1) -> int:
        """Remove files older than specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        deleted_count = 0
        
        try:
            for file_path in self.upload_dir.glob('*'):
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        file_path.unlink()
                        deleted_count += 1
                        logger.debug(f"Deleted old file: {file_path.name}")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
        
        if deleted_count > 0:
            logger.info(f"Cleanup completed: {deleted_count} files deleted")
        
        return deleted_count
    
    def get_file_info(self, file_path: str) -> dict:
        """Get file information"""
        path = Path(file_path)
        if not path.exists():
            return {"exists": False}
        
        stat = path.stat()
        return {
            "exists": True,
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "name": path.name
        }

# Made with Bob
