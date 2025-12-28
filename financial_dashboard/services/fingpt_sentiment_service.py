"""
FinGPT Sentiment Analysis Service
=================================
Provides financial sentiment analysis using FinGPT v3.3 (Llama2-13b with LoRA).
Falls back to rule-based sentiment if GPU/model not available.

Models used:
- Base: NousResearch/Llama-2-13b-hf (or 7b for lower memory)
- LoRA: FinGPT/fingpt-sentiment_llama2-13b_lora
"""

import os
import logging
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Global model cache
_fingpt_model = None
_fingpt_tokenizer = None
_fingpt_available = False


def is_fingpt_available() -> bool:
    """Check if FinGPT model is loaded and available."""
    return _fingpt_available


def load_fingpt_model(use_8bit: bool = True, model_size: str = "7b") -> bool:
    """
    Load FinGPT sentiment model with LoRA adapter.
    
    Args:
        use_8bit: Use 8-bit quantization for lower memory usage
        model_size: "7b" or "13b" - 7b uses less memory
        
    Returns:
        True if model loaded successfully, False otherwise
    """
    global _fingpt_model, _fingpt_tokenizer, _fingpt_available
    
    if _fingpt_available:
        return True
    
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, LlamaTokenizerFast
        from peft import PeftModel
        
        # Check GPU availability
        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cpu":
            logger.warning("No GPU available - FinGPT will be slow on CPU")
        
        # Select model based on size
        if model_size == "13b":
            base_model_name = "NousResearch/Llama-2-13b-hf"
            peft_model_name = "FinGPT/fingpt-sentiment_llama2-13b_lora"
        else:
            base_model_name = "meta-llama/Llama-2-7b-chat-hf"
            peft_model_name = "FinGPT/fingpt-sentiment_llama2-7b_lora"
        
        logger.info(f"Loading FinGPT base model: {base_model_name}")
        
        # Load tokenizer
        _fingpt_tokenizer = LlamaTokenizerFast.from_pretrained(
            base_model_name, 
            trust_remote_code=True
        )
        _fingpt_tokenizer.pad_token = _fingpt_tokenizer.eos_token
        
        # Load model with optional 8-bit quantization
        load_kwargs = {
            "trust_remote_code": True,
            "device_map": "auto" if device == "cuda" else None,
        }
        
        if use_8bit and device == "cuda":
            load_kwargs["load_in_8bit"] = True
        elif device == "cuda":
            load_kwargs["torch_dtype"] = torch.float16
        
        base_model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            **load_kwargs
        )
        
        # Load LoRA adapter
        logger.info(f"Loading FinGPT LoRA adapter: {peft_model_name}")
        _fingpt_model = PeftModel.from_pretrained(base_model, peft_model_name)
        _fingpt_model = _fingpt_model.eval()
        
        _fingpt_available = True
        logger.info("✅ FinGPT sentiment model loaded successfully")
        return True
        
    except ImportError as e:
        logger.error(f"Missing dependencies for FinGPT: {e}")
        logger.info("Install with: pip install peft bitsandbytes accelerate")
        return False
    except Exception as e:
        logger.error(f"Failed to load FinGPT model: {e}")
        return False


def analyze_sentiment_fingpt(text: str) -> Dict:
    """
    Analyze sentiment using FinGPT model.
    
    Args:
        text: Financial news or tweet text to analyze
        
    Returns:
        Dict with sentiment, confidence, and raw response
    """
    global _fingpt_model, _fingpt_tokenizer, _fingpt_available
    
    if not _fingpt_available:
        return analyze_sentiment_fallback(text)
    
    try:
        import torch
        
        # FinGPT prompt format
        prompt = f"""Instruction: What is the sentiment of this news? Please choose an answer from {{negative/neutral/positive}}
Input: {text}
Answer: """
        
        # Tokenize
        inputs = _fingpt_tokenizer(
            prompt, 
            return_tensors='pt', 
            padding=True, 
            max_length=512,
            truncation=True
        )
        
        # Move to same device as model
        device = next(_fingpt_model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Generate
        with torch.no_grad():
            outputs = _fingpt_model.generate(
                **inputs,
                max_new_tokens=10,
                do_sample=False,
                pad_token_id=_fingpt_tokenizer.eos_token_id
            )
        
        # Decode
        response = _fingpt_tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Extract sentiment from response
        answer = response.split("Answer:")[-1].strip().lower()
        
        if "positive" in answer:
            sentiment = "positive"
            score = 0.8
        elif "negative" in answer:
            sentiment = "negative"
            score = -0.8
        else:
            sentiment = "neutral"
            score = 0.0
        
        return {
            "sentiment": sentiment,
            "score": score,
            "confidence": 0.85,  # FinGPT v3.3 has ~88% F1
            "model": "FinGPT-v3.3",
            "raw_response": answer,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"FinGPT inference failed: {e}")
        return analyze_sentiment_fallback(text)


def analyze_sentiment_fallback(text: str) -> Dict:
    """
    Simple rule-based sentiment fallback when FinGPT is not available.
    """
    text_lower = text.lower()
    
    # Positive keywords
    positive_words = ["surge", "gain", "rise", "profit", "growth", "beat", "strong", 
                      "bullish", "upgrade", "buy", "outperform", "record", "soar"]
    # Negative keywords                  
    negative_words = ["drop", "fall", "loss", "decline", "miss", "weak", "bearish",
                      "downgrade", "sell", "underperform", "crash", "plunge", "concern"]
    
    pos_count = sum(1 for w in positive_words if w in text_lower)
    neg_count = sum(1 for w in negative_words if w in text_lower)
    
    if pos_count > neg_count:
        sentiment = "positive"
        score = min(0.3 + (pos_count * 0.1), 0.7)
    elif neg_count > pos_count:
        sentiment = "negative"
        score = max(-0.3 - (neg_count * 0.1), -0.7)
    else:
        sentiment = "neutral"
        score = 0.0
    
    return {
        "sentiment": sentiment,
        "score": score,
        "confidence": 0.5,  # Lower confidence for rule-based
        "model": "rule-based",
        "raw_response": f"pos:{pos_count}, neg:{neg_count}",
        "timestamp": datetime.now().isoformat()
    }


def analyze_batch_sentiment(texts: List[str]) -> List[Dict]:
    """Analyze sentiment for multiple texts."""
    return [analyze_sentiment_fingpt(t) for t in texts]


# Initialize on import if GPU available
def init_fingpt_on_startup():
    """Attempt to load FinGPT on startup (non-blocking)."""
    import threading
    
    def _load():
        try:
            import torch
            if torch.cuda.is_available():
                load_fingpt_model(use_8bit=True, model_size="7b")
            else:
                logger.info("Skipping FinGPT load - no GPU. Using fallback sentiment.")
        except Exception as e:
            logger.warning(f"FinGPT startup load failed: {e}")
    
    # Load in background thread to not block startup
    thread = threading.Thread(target=_load, daemon=True)
    thread.start()
