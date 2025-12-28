#!/bin/bash
# Configure environment for HuggingFace LLM (free, no OpenAI)
# This ensures NO mock mode is used

# Set LLM backend to HuggingFace
export LLM_BACKEND=huggingface

# Configure HuggingFace model (TinyLlama is fast and free)
export HF_MODEL_NAME=TinyLlama/TinyLlama-1.1B-Chat-v1.0

# Enable 8-bit quantization for memory efficiency
export HF_LOAD_IN_8BIT=1

# Max generation length
export HF_MAX_LENGTH=512

# Disable mock mode explicitly
export USE_MOCK_ADAPTER=0

echo "✅ HuggingFace LLM configured:"
echo "   Backend: $LLM_BACKEND"
echo "   Model: $HF_MODEL_NAME"
echo "   8-bit quantization: $HF_LOAD_IN_8BIT"
echo ""
echo "Starting dashboard with real LLM..."
