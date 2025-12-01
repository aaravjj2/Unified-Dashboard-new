"""Simple mock Bento predictor for offline testing."""

def predict(payload):
    # Return a deterministic mock response
    return {'response': 'This is a mock prediction for ' + str(payload.get('text', ''))}
