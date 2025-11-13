"""
Helper utilities for the application.

This module contains common utility classes and functions.
"""

import time


class Timer:
    """
    Context manager for timing operations.
    
    Usage:
        with Timer() as t:
            # code to time
        elapsed_time = t.elapsed
    """
    def __init__(self):
        self.elapsed = 0
        self._start_time = 0
        
    def __enter__(self):
        self._start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = time.time() - self._start_time

# Made with Bob
