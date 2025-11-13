"""
Model management module.

This module handles loading and managing the language model and tokenizer.
"""

import logging
import time
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import Optional, Tuple
from .config import settings

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages the language model and tokenizer lifecycle."""
    
    def __init__(self):
        self.model: Optional[AutoModelForCausalLM] = None
        self.tokenizer: Optional[AutoTokenizer] = None
        self.device: str = "cpu"
        
    def load_model(self) -> Tuple[AutoModelForCausalLM, AutoTokenizer, str]:
        """
        Load the model and tokenizer.
        
        Returns:
            Tuple of (model, tokenizer, device)
        """
        logger.info("Loading model and tokenizer...")
        start_time = time.time()
        
        try:
            # Set device
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device: {self.device}")
            
            # Load model and tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(settings.MODEL_PATH)
            self.model = AutoModelForCausalLM.from_pretrained(
                settings.MODEL_PATH,
                device_map=self.device
            )
            self.model.eval()
            
            elapsed = time.time() - start_time
            logger.info(f"Model loaded successfully in {elapsed:.2f} seconds")
            
            return self.model, self.tokenizer, self.device
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise e
    
    def is_loaded(self) -> bool:
        """Check if model and tokenizer are loaded."""
        return self.model is not None and self.tokenizer is not None
    
    def get_model(self) -> AutoModelForCausalLM:
        """Get the loaded model."""
        if self.model is None:
            raise RuntimeError("Model not loaded")
        return self.model
    
    def get_tokenizer(self) -> AutoTokenizer:
        """Get the loaded tokenizer."""
        if self.tokenizer is None:
            raise RuntimeError("Tokenizer not loaded")
        return self.tokenizer
    
    def get_device(self) -> str:
        """Get the device being used."""
        return self.device


# Global model manager instance
model_manager = ModelManager()

# Made with Bob
