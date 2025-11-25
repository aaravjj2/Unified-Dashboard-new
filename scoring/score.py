import os
import joblib
import json


def _resolve_model_path():
    """Resolve model path for use inside Azure ML deployments and local runs.

    Priority:
      1. MODEL_PATH environment variable (absolute path to the model file)
      2. AZUREML_MODEL_DIR environment variable (common in Azure ML runtime) + MODEL_FILE name
      3. Relative repo path ../models/<MODEL_FILE>

    Returns absolute path to model file (may not exist — caller will get a clear error).
    """
    # 1) explicit override
    model_path_env = os.environ.get('MODEL_PATH')
    if model_path_env:
        return os.path.abspath(model_path_env)

    # model filename may be overridden (defaults to portfolio_model.pkl)
    model_filename = os.environ.get('MODEL_FILE', 'portfolio_model.pkl')

    # 2) Azure ML runtime directory where registered models are mounted
    azureml_dir = os.environ.get('AZUREML_MODEL_DIR')
    if azureml_dir:
        candidate = os.path.join(azureml_dir, model_filename)
        if os.path.exists(candidate):
            return os.path.abspath(candidate)

    # 3) fallback to the repo relative path (keeps previous behaviour)
    candidate = os.path.join(os.path.dirname(__file__), '..', 'models', model_filename)
    return os.path.abspath(candidate)


MODEL_PATH = _resolve_model_path()


def init():
    """Load the model into a module-level variable `model`.

    Raises a RuntimeError with a helpful message if loading fails.
    """
    global model
    try:
        model = joblib.load(MODEL_PATH)
    except Exception as exc:
        # surface a clear error that includes the resolved path for debugging/support
        raise RuntimeError(f"Failed to load model at {MODEL_PATH}: {exc}") from exc


def run(request_json):
    # Expect JSON like {"inputs": [[...], [...]]}
    data = request_json.get('inputs') if isinstance(request_json, dict) else None
    if data is None:
        return {"error": "invalid input"}

    preds = model.predict(data)

    # ensure predictions are JSON-serializable
    try:
        return {"predictions": preds.tolist()}
    except Exception:
        # fall back to converting scalars
        try:
            return {"predictions": [float(x) for x in preds]}
        except Exception:
            # last resort: return stringified predictions
            return {"predictions": [str(x) for x in preds]}