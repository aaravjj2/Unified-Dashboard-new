"""
Generator Client - Local LLM Interface (gpt4all/falcon)
Wraps local gpt4all/falcon instance with retry/backoff and streaming support
"""

import os
import time
import logging
import subprocess
import json
from typing import Optional, Dict, Any, Generator
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GeneratorResponse:
    """Response from the generator"""
    text: str
    model: str
    completion_tokens: int
    prompt_tokens: int
    total_tokens: int
    finish_reason: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "model": self.model,
            "completion_tokens": self.completion_tokens,
            "prompt_tokens": self.prompt_tokens,
            "total_tokens": self.total_tokens,
            "finish_reason": self.finish_reason
        }


class GeneratorClient:
    """
    Local LLM generator client (gpt4all/falcon)
    
    Supports:
    - Synchronous and streaming completion
    - Retry with exponential backoff
    - Timeout handling
    - Health checks
    """
    
    def __init__(
        self,
        model_name: str = "orca-mini-3b-gguf2-q4_0.gguf",
        model_path: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 30,
        deterministic: bool = False
    ):
        """
        Initialize generator client
        
        Args:
            model_name: Name of the gpt4all model
            model_path: Optional path to model file
            max_retries: Maximum retry attempts
            timeout: Request timeout in seconds
            deterministic: If True, use reduced temperature and canned responses
        """
        self.model_name = model_name
        self.model_path = model_path or os.getenv("GPT4ALL_MODEL_PATH", "")
        self.max_retries = max_retries
        self.timeout = timeout
        self.deterministic = deterministic or os.getenv("OPTIONS_DETERMINISTIC") == "1"
        
        # Try to import gpt4all
        try:
            from gpt4all import GPT4All
            self.gpt4all = GPT4All
            self.has_gpt4all = True
            logger.info(f"gpt4all library loaded successfully")
        except ImportError:
            self.has_gpt4all = False
            logger.warning("gpt4all not available, using mock mode")
            
        self._model_instance = None
        
    def _get_model(self):
        """Lazy load model instance"""
        if self._model_instance is None and self.has_gpt4all:
            try:
                # Load model (CPU mode - GPU hangs on this system)
                # Note: CPU inference measured at ~4-5s for simple queries
                # Prefer passing explicit model_path when available so GPT4All can locate the file
                if self.model_path:
                    # If model_path is a directory, pass model_path and model_name separately
                    if os.path.isdir(self.model_path):
                        self._model_instance = self.gpt4all(model_name=self.model_name, model_path=self.model_path)
                    else:
                        # model_path may be a full file path
                        self._model_instance = self.gpt4all(model_name=os.path.basename(self.model_path), model_path=os.path.dirname(self.model_path))
                else:
                    self._model_instance = self.gpt4all(self.model_name)
                logger.info(f"Loaded model: {self.model_name} (path={self.model_path or 'default'}) on CPU")
            except Exception as e:
                logger.error(f"Failed to load model {self.model_name}: {e}")
                raise
        return self._model_instance
    
    def complete(
        self,
        prompt: str,
        max_tokens: int = 256,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stream: bool = False
    ) -> GeneratorResponse:
        """
        Complete a prompt using the local generator
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 = deterministic)
            top_p: Nucleus sampling parameter
            stream: If True, return streaming generator
            
        Returns:
            GeneratorResponse with generated text and metadata
        """
        # Deterministic mode overrides
        if self.deterministic:
            temperature = 0.1
            return self._deterministic_response(prompt)
        
        # Mock mode fallback
        if not self.has_gpt4all:
            return self._mock_response(prompt)
        
        # Retry loop with exponential backoff
        for attempt in range(self.max_retries):
            try:
                model = self._get_model()
                start_time = time.time()
                
                # Generate completion
                with_context = model.generate(
                    prompt,
                    max_tokens=max_tokens,
                    temp=temperature,
                    top_p=top_p,
                    streaming=stream
                )
                
                # Handle streaming vs synchronous
                if stream:
                    return self._streaming_response(with_context, prompt)
                else:
                    output = with_context
                    elapsed = time.time() - start_time
                    
                    # Estimate token counts (rough approximation)
                    prompt_tokens = len(prompt.split()) * 1.3
                    completion_tokens = len(output.split()) * 1.3
                    
                    logger.info(f"Generated {completion_tokens} tokens in {elapsed:.2f}s")
                    
                    return GeneratorResponse(
                        text=output,
                        model=self.model_name,
                        completion_tokens=int(completion_tokens),
                        prompt_tokens=int(prompt_tokens),
                        total_tokens=int(prompt_tokens + completion_tokens),
                        finish_reason="stop"
                    )
                    
            except Exception as e:
                logger.error(f"Generator attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    backoff = 2 ** attempt
                    logger.info(f"Retrying in {backoff}s...")
                    time.sleep(backoff)
                else:
                    raise
        
        raise RuntimeError(f"Generator failed after {self.max_retries} attempts")
    
    def _streaming_response(self, stream_gen, prompt: str) -> Generator[str, None, None]:
        """Handle streaming generator"""
        for token in stream_gen:
            yield token
    
    def _deterministic_response(self, prompt: str) -> GeneratorResponse:
        """
        Return deterministic canned response for testing
        """
        # Simple keyword-based deterministic responses
        prompt_lower = prompt.lower()
        
        if "volatility" in prompt_lower or "vol" in prompt_lower:
            text = "Based on the volatility data, AAPL shows elevated implied volatility in near-term options. Source: vol_surface_aapl.json"
        elif "summarize" in prompt_lower:
            text = "Summary: The latest market data indicates stable positions with moderate volatility. Source: positions_snapshot.json"
        elif "trade" in prompt_lower or "order" in prompt_lower:
            text = json.dumps({
                "action": "create_paper_order",
                "payload": {
                    "symbol": "AAPL",
                    "qty": 1,
                    "side": "buy",
                    "type": "market"
                },
                "confidence": 0.85
            })
        else:
            text = "I can help you analyze market data, volatility, and suggest paper trades. What would you like to know?"
        
        return GeneratorResponse(
            text=text,
            model="deterministic-fixture",
            completion_tokens=len(text.split()),
            prompt_tokens=len(prompt.split()),
            total_tokens=len(text.split()) + len(prompt.split()),
            finish_reason="stop"
        )
    
    def _mock_response(self, prompt: str) -> GeneratorResponse:
        """
        Mock response when gpt4all unavailable
        """
        mock_text = f"[MOCK] I received your query: '{prompt[:50]}...' but gpt4all is not available. Install with: pip install gpt4all"
        
        return GeneratorResponse(
            text=mock_text,
            model="mock",
            completion_tokens=len(mock_text.split()),
            prompt_tokens=len(prompt.split()),
            total_tokens=len(mock_text.split()) + len(prompt.split()),
            finish_reason="mock"
        )
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check generator health and responsiveness
        
        Returns:
            Dict with status, model info, and response time
        """
        try:
            start = time.time()
            
            if not self.has_gpt4all:
                return {
                    "status": "degraded",
                    "model": "mock",
                    "available": False,
                    "error": "gpt4all not installed",
                    "response_time_ms": 0
                }
            
            # Simple test prompt
            response = self.complete("Hi", max_tokens=10, temperature=0.1)
            elapsed_ms = (time.time() - start) * 1000
            
            return {
                "status": "healthy",
                "model": self.model_name,
                "available": True,
                "response_time_ms": elapsed_ms,
                "test_tokens": response.completion_tokens
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "model": self.model_name,
                "available": False,
                "error": str(e),
                "response_time_ms": 0
            }


# Global singleton instance
_generator_instance: Optional[GeneratorClient] = None


def get_generator() -> GeneratorClient:
    """Get or create global generator instance"""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = GeneratorClient()
    return _generator_instance
