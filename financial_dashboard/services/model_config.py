"""
Model Configuration for FinGPT Integration

Centralized configuration for selecting and configuring LLM adapters.
Supports multiple backends: HuggingFace (local), OpenAI, or Mock.

Environment Variables:
    LLM_BACKEND: 'huggingface', 'openai', or 'mock' (default: 'mock')
    
    For HuggingFace:
        HF_MODEL_NAME: Model name or path (default: 'TinyLlama/TinyLlama-1.1B-Chat-v1.0')
        HF_LOAD_IN_8BIT: '1' to enable 8-bit quantization
        HF_LOAD_IN_4BIT: '1' to enable 4-bit quantization
        HF_MAX_LENGTH: Max generation length (default: 512)
    
    For OpenAI:
        OPENAI_API_KEY: API key (required)
        OPENAI_MODEL: Model name (default: 'gpt-3.5-turbo')
        OPENAI_MAX_TOKENS: Max tokens (default: 500)
"""

import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


# Default configurations for each backend
DEFAULT_CONFIGS = {
    'huggingface': {
        'model_path': 'TinyLlama/TinyLlama-1.1B-Chat-v1.0',  # Small, fast model for testing
        'load_in_8bit': False,
        'load_in_4bit': False,
        'max_length': 512,
        'device': 'auto'
    },
    'openai': {
        'api_key': None,  # Must be provided via env
        'model': 'gpt-3.5-turbo',
        'max_tokens': 500,
        'temperature': 0.7
    },
    'mock': {
        'name': 'mock',
        'type': 'mock'
    }
}


def get_llm_backend() -> str:
    """
    Get the configured LLM backend from environment.
    
    Returns:
        'huggingface', 'openai', or 'mock'
    """
    backend = os.getenv('LLM_BACKEND', 'mock').lower()
    
    if backend not in ['huggingface', 'openai', 'mock']:
        logger.warning(f"Invalid LLM_BACKEND '{backend}', defaulting to 'mock'")
        return 'mock'
    
    return backend


def get_huggingface_config() -> Dict[str, Any]:
    """Get HuggingFace model configuration from environment."""
    config = DEFAULT_CONFIGS['huggingface'].copy()
    
    # Override with environment variables
    if os.getenv('HF_MODEL_NAME'):
        config['model_path'] = os.getenv('HF_MODEL_NAME')
    
    if os.getenv('HF_LOAD_IN_8BIT', '').lower() in ('1', 'true', 'yes'):
        config['load_in_8bit'] = True
        config['load_in_4bit'] = False  # Mutually exclusive
    
    if os.getenv('HF_LOAD_IN_4BIT', '').lower() in ('1', 'true', 'yes'):
        config['load_in_4bit'] = True
        config['load_in_8bit'] = False  # Mutually exclusive
    
    if os.getenv('HF_MAX_LENGTH'):
        try:
            config['max_length'] = int(os.getenv('HF_MAX_LENGTH'))
        except ValueError:
            pass
    
    return config


def get_openai_config() -> Dict[str, Any]:
    """Get OpenAI configuration from environment."""
    config = DEFAULT_CONFIGS['openai'].copy()
    
    # API key is required
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI backend")
    
    config['api_key'] = api_key
    
    # Override with environment variables
    if os.getenv('OPENAI_MODEL'):
        config['model'] = os.getenv('OPENAI_MODEL')
    
    if os.getenv('OPENAI_MAX_TOKENS'):
        try:
            config['max_tokens'] = int(os.getenv('OPENAI_MAX_TOKENS'))
        except ValueError:
            pass
    
    if os.getenv('OPENAI_TEMPERATURE'):
        try:
            config['temperature'] = float(os.getenv('OPENAI_TEMPERATURE'))
        except ValueError:
            pass
    
    return config


def get_model_adapter():
    """
    Get the configured model adapter based on environment settings.
    
    Returns:
        ModelAdapter instance (HuggingFaceLoRAAdapter, OpenAIAdapter, or MockAdapter)
    """
    backend = get_llm_backend()
    
    logger.info(f"🤖 Initializing LLM backend: {backend}")
    
    if backend == 'huggingface':
        try:
            from financial_dashboard.models.hf_lora import HuggingFaceLoRAAdapter
            
            config = get_huggingface_config()
            logger.info(f"Loading HuggingFace model: {config['model_path']}")
            
            adapter = HuggingFaceLoRAAdapter(config)
            logger.info("✅ HuggingFace adapter initialized")
            return adapter
            
        except Exception as e:
            logger.error(f"Failed to initialize HuggingFace adapter: {e}")
            logger.warning("Falling back to Mock adapter")
            from financial_dashboard.models.adapters import MockAdapter
            return MockAdapter(DEFAULT_CONFIGS['mock'])
    
    elif backend == 'openai':
        try:
            from financial_dashboard.models.openai_adapter import OpenAIAdapter
            
            config = get_openai_config()
            logger.info(f"Using OpenAI model: {config['model']}")
            
            adapter = OpenAIAdapter(config)
            logger.info("✅ OpenAI adapter initialized")
            return adapter
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI adapter: {e}")
            logger.warning("Falling back to Mock adapter")
            from financial_dashboard.models.adapters import MockAdapter
            return MockAdapter(DEFAULT_CONFIGS['mock'])
    
    else:  # mock
        from financial_dashboard.models.adapters import MockAdapter
        logger.info("Using Mock adapter (no real LLM)")
        return MockAdapter(DEFAULT_CONFIGS['mock'])


def get_adapter_info() -> Dict[str, Any]:
    """
    Get information about the current adapter configuration.
    
    Returns:
        Dict with backend type, model name, and configuration details
    """
    backend = get_llm_backend()
    
    info = {
        'backend': backend,
        'model': None,
        'quantization': None,
        'status': 'configured'
    }
    
    if backend == 'huggingface':
        config = get_huggingface_config()
        info['model'] = config['model_path']
        if config['load_in_8bit']:
            info['quantization'] = '8-bit'
        elif config['load_in_4bit']:
            info['quantization'] = '4-bit'
        else:
            info['quantization'] = 'none'
    
    elif backend == 'openai':
        try:
            config = get_openai_config()
            info['model'] = config['model']
            info['api_configured'] = bool(config['api_key'])
        except Exception:
            info['status'] = 'api_key_missing'
    
    else:  # mock
        info['model'] = 'mock'
        info['status'] = 'mock_mode'
    
    return info


# Singleton adapter instance (lazy-loaded)
_adapter_instance = None


def get_default_adapter():
    """
    Get the default adapter instance (singleton).
    Adapter is initialized once and reused.
    """
    global _adapter_instance
    
    if _adapter_instance is None:
        _adapter_instance = get_model_adapter()
    
    return _adapter_instance


def reset_adapter():
    """Reset the adapter instance (force reinitialization)."""
    global _adapter_instance
    _adapter_instance = None
