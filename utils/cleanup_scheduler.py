from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import logging

logger = logging.getLogger(__name__)

class CleanupScheduler:
    """Manages background cleanup tasks"""
    
    def __init__(self, file_manager, cache_manager):
        self.scheduler = AsyncIOScheduler()
        self.file_manager = file_manager
        self.cache_manager = cache_manager
        logger.info("CleanupScheduler initialized")
    
    def start(self):
        """Start scheduled cleanup tasks"""
        # Cleanup old files every hour
        self.scheduler.add_job(
            self._cleanup_files,
            trigger=IntervalTrigger(hours=1),
            id='cleanup_files',
            name='Cleanup old uploaded files',
            replace_existing=True
        )
        
        # Cleanup expired cache every 6 hours
        self.scheduler.add_job(
            self._cleanup_cache,
            trigger=IntervalTrigger(hours=6),
            id='cleanup_cache',
            name='Cleanup expired cache',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info("Cleanup scheduler started")
    
    def _cleanup_files(self):
        """Cleanup old uploaded files"""
        try:
            deleted = self.file_manager.cleanup_old_files(max_age_hours=1)
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old files")
        except Exception as e:
            logger.error(f"Error cleaning up files: {str(e)}")
    
    def _cleanup_cache(self):
        """Cleanup expired cache entries"""
        try:
            self.cache_manager.clear_expired()
            logger.info("Cache cleanup completed")
        except Exception as e:
            logger.error(f"Error cleaning up cache: {str(e)}")
    
    def shutdown(self):
        """Shutdown scheduler"""
        try:
            self.scheduler.shutdown()
            logger.info("Cleanup scheduler stopped")
        except Exception as e:
            logger.error(f"Error shutting down scheduler: {str(e)}")

# Made with Bob
