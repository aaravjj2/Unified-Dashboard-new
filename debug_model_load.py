from gpt4all import GPT4All
import time
import sys

import os

# Prefer env var overrides when debugging
model_path = os.getenv("GPT4ALL_MODEL_PATH", os.path.join(os.path.expanduser("~"), "Unified-Dashboard", "models"))
model_file = os.getenv("GPT4ALL_MODEL", "mistral-7b-instruct-v0.2.Q4_K_M.gguf")

print(f"Attempting to load {model_file}...")
start = time.time()

try:
    # Try with 'cuda' first as in the service
    print("Trying device='cuda'...")
    model = GPT4All(
        model_name=model_file,
        model_path=model_path,
        device='cuda',
        n_threads=8
    )
    print(f"Successfully loaded on CUDA in {time.time() - start:.2f}s")
    
    # Generate a small test
    print("Generating test response...")
    res = model.generate("Hello, are you working?", max_tokens=20)
    print(f"Response: {res}")
    
except Exception as e:
    print(f"Failed on CUDA: {e}")
    
    # Try CPU fallback
    print("\nTrying device='cpu'...")
    try:
        start = time.time()
        model = GPT4All(
            model_name=model_file,
            model_path=model_path,
            device='cpu',
            n_threads=8
        )
        print(f"Successfully loaded on CPU in {time.time() - start:.2f}s")
        res = model.generate("Hello, are you working?", max_tokens=20)
        print(f"Response: {res}")
    except Exception as e2:
        print(f"Failed on CPU: {e2}")
