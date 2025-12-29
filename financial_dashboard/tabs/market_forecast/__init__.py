"""Market forecast package initialization."""
from pathlib import Path

# Create cache directory for neural models
CACHE_DIR = Path(__file__).parent.parent.parent.parent / 'cache' / 'neural_models'
CACHE_DIR.mkdir(parents=True, exist_ok=True)
