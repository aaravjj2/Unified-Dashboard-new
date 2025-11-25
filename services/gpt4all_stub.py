# services/gpt4all_stub.py
"""
GPT4All Local Stub Service
Provides deterministic mock responses when actual model is unavailable.
"""
from flask import Flask, request, jsonify
import os
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
MODEL_PATH = os.getenv("GPT4ALL_MODEL_PATH", "/models/gpt4all.bin")

@app.route("/healthz")
def health():
    """Health check endpoint"""
    if os.path.exists(MODEL_PATH):
        return jsonify({
            "model": "gpt4all",
            "status": "ready",
            "path": MODEL_PATH
        })
    else:
        return jsonify({
            "model": "gpt4all", 
            "status": "mock",
            "message": "Model file not found, returning deterministic mock responses"
        })

@app.route("/api/chat", methods=["POST"])
def chat():
    """Chat endpoint - deterministic mock or local inference"""
    payload = request.json or {}
    prompt = payload.get("prompt", "")
    
    logger.info(f"Chat request: {prompt[:100]}")
    
    # Deterministic mock reply if model not available
    if not os.path.exists(MODEL_PATH):
        # Simple keyword-based responses for testing
        response_text = "[MOCK] "
        prompt_lower = prompt.lower()
        
        if "p/e" in prompt_lower or "price" in prompt_lower and "earnings" in prompt_lower:
            response_text += "P/E ratio is Price-to-Earnings, calculated as stock price divided by earnings per share."
        elif "backtest" in prompt_lower:
            response_text += "Backtesting tests a trading strategy using historical data to evaluate performance."
        elif "options" in prompt_lower:
            response_text += "Options are financial derivatives giving the right (not obligation) to buy/sell at a specific price."
        else:
            response_text += f"Mock response for: '{prompt[:50]}...'"
        
        return jsonify({
            "mock": True,
            "text": response_text,
            "model": "gpt4all-stub",
            "timestamp": time.time()
        })
    
    # If model exists, this is where local inference would be called
    # For now, return a placeholder
    return jsonify({
        "mock": False,
        "text": "[LOCAL MODEL] Inference not yet implemented in stub",
        "model": "gpt4all-local",
        "timestamp": time.time()
    })

if __name__ == "__main__":
    logger.info(f"Starting GPT4All stub service on 0.0.0.0:8080")
    logger.info(f"Model path: {MODEL_PATH}")
    logger.info(f"Model exists: {os.path.exists(MODEL_PATH)}")
    app.run(host="0.0.0.0", port=8080)
