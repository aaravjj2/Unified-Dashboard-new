"""
Shared LLM Client
=================
Provides a unified interface for interacting with Local LLMs (Ollama, GPT4All).
"""

import os
import logging
import httpx
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class LLMClient:
    """Client for interacting with local LLMs."""
    
    def __init__(self):
        self.backend = None
        self.model_name = None
        self.ollama_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.http_client = httpx.Client(timeout=120.0)
        self._gpt4all_model = None
        
        self._initialize_backend()
        
    def _initialize_backend(self):
        """Initialize the best available backend."""
        # 1. Try Ollama first (preferred for GPU support)
        try:
            response = self.http_client.get(f"{self.ollama_url}/api/tags", timeout=2.0)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                
                # Look for preferred models
                preferred = ["mistral", "llama3", "gemma"]
                for p in preferred:
                    found = next((m for m in model_names if p in m.lower()), None)
                    if found:
                        self.backend = "ollama"
                        self.model_name = found
                        logger.info(f"✅ LLM Client: Connected to Ollama ({self.model_name})")
                        return
        except Exception as e:
            logger.debug(f"Ollama check failed: {e}")
            
        # 2. Fallback to GPT4All
        try:
            from gpt4all import GPT4All
            model_path = os.getenv("GPT4ALL_MODEL_PATH", os.path.join(os.path.expanduser("~"), "Unified-Dashboard", "models"))
            model_file = os.getenv("GPT4ALL_MODEL", "mistral-7b-instruct-v0.2.Q4_K_M.gguf")
            full_path = os.path.join(model_path, model_file)
            
            if os.path.exists(full_path):
                self._gpt4all_model = GPT4All(
                    model_name=model_file,
                    model_path=model_path,
                    device='cpu',
                    n_threads=8
                )
                self.backend = "gpt4all"
                self.model_name = model_file
                logger.info(f"✅ LLM Client: Loaded GPT4All ({self.model_name})")
                return
        except Exception as e:
            logger.warning(f"GPT4All initialization failed: {e}")
            
        logger.warning("⚠️ LLM Client: No local LLM found. Using rule-based fallback.")
        
    def generate(self, prompt: str, max_tokens: int = 500, temperature: float = 0.7) -> str:
        """Generate text from the LLM."""
        if not self.backend:
            return "AI generation unavailable. Please ensure Ollama or GPT4All is configured."
            
        try:
            if self.backend == "ollama":
                payload = {
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature
                    }
                }
                response = self.http_client.post(f"{self.ollama_url}/api/generate", json=payload)
                if response.status_code == 200:
                    return response.json().get("response", "").strip()
                    
            elif self.backend == "gpt4all" and self._gpt4all_model:
                return self._gpt4all_model.generate(
                    prompt, 
                    max_tokens=max_tokens, 
                    temp=temperature
                ).strip()
                
        except Exception as e:
            logger.error(f"Generation failed ({self.backend}): {e}")
            
        return "Error generating AI response."

# Singleton instance
_client = None

def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
