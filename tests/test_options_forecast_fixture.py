"""
Unit test for Options Forecast API endpoint

Tests deterministic fixture behavior per Phase 31 STEP 3 requirements.

Author: Agent 1A
Phase: 31 STEP 3
"""

import pytest
import json
import os
import sys

# Add parent dir to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from financial_dashboard.app import create_app


@pytest.fixture
def client():
    """Flask test client with OPTIONS_DETERMINISTIC=1"""
    os.environ['OPTIONS_DETERMINISTIC'] = '1'
    app = create_app()
    # Dash apps don't use app.config['TESTING'], use server directly
    app.server.config['TESTING'] = True
    
    with app.server.test_client() as client:
        yield client


def test_options_forecast_deterministic(client):
    """Test POST /api/options/forecast with deterministic=True"""
    
    payload = {
        'ticker': 'AAPL',
        'expiration_days': 30,
        'deterministic': True
    }
    
    response = client.post(
        '/api/options/forecast',
        data=json.dumps(payload),
        content_type='application/json'
    )
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    data = response.get_json()
    
    # Validate response schema
    assert 'error' in data, "Response missing 'error' field"
    assert data['error'] == False, "Expected error=False for deterministic mode"
    
    assert 'result' in data, "Response missing 'result' field"
    result = data['result']
    
    # Validate result structure
    assert 'forecast_series' in result, "Missing forecast_series"
    assert 'term_structure' in result, "Missing term_structure"
    assert 'surface_grid' in result, "Missing surface_grid"
    assert 'metrics' in result, "Missing metrics"
    assert 'explanation' in result, "Missing explanation"
    
    # Validate forecast_series
    assert isinstance(result['forecast_series'], list), "forecast_series should be list"
    assert len(result['forecast_series']) >= 5, "forecast_series should have at least 5 entries"
    
    for entry in result['forecast_series']:
        assert 'date' in entry, "Forecast entry missing date"
        assert 'predicted_iv' in entry, "Forecast entry missing predicted_iv"
        assert 'lower_bound' in entry, "Forecast entry missing lower_bound"
        assert 'upper_bound' in entry, "Forecast entry missing upper_bound"
        assert 'confidence' in entry, "Forecast entry missing confidence"
        
        # Validate IV ranges
        assert 0.01 <= entry['predicted_iv'] <= 3.0, f"predicted_iv out of range: {entry['predicted_iv']}"
        assert 0.01 <= entry['lower_bound'] <= 3.0, f"lower_bound out of range"
        assert 0.01 <= entry['upper_bound'] <= 3.0, f"upper_bound out of range"
        assert 0.0 <= entry['confidence'] <= 1.0, f"confidence out of range: {entry['confidence']}"
    
    # Validate term_structure
    assert isinstance(result['term_structure'], list), "term_structure should be list"
    assert len(result['term_structure']) >= 5, "term_structure should have at least 5 entries"
    
    for term in result['term_structure']:
        assert 'days_to_expiry' in term, "Term entry missing days_to_expiry"
        assert 'atm_iv' in term, "Term entry missing atm_iv"
        assert 0.01 <= term['atm_iv'] <= 3.0, f"atm_iv out of range: {term['atm_iv']}"
    
    # Validate surface_grid
    surface = result['surface_grid']
    assert 'strikes' in surface, "surface_grid missing strikes"
    assert 'expirations' in surface, "surface_grid missing expirations"
    assert 'iv_matrix' in surface, "surface_grid missing iv_matrix"
    
    assert isinstance(surface['strikes'], list), "strikes should be list"
    assert len(surface['strikes']) >= 5, "strikes should have at least 5 values"
    
    assert isinstance(surface['expirations'], list), "expirations should be list"
    assert len(surface['expirations']) >= 5, "expirations should have at least 5 values"
    
    assert isinstance(surface['iv_matrix'], list), "iv_matrix should be list"
    assert len(surface['iv_matrix']) >= 5, "iv_matrix should have at least 5 rows"
    
    for row in surface['iv_matrix']:
        assert len(row) >= 5, "Each iv_matrix row should have at least 5 values"
        for iv in row:
            assert 0.01 <= iv <= 3.0, f"IV out of range: {iv}"
    
    # Validate metrics
    metrics = result['metrics']
    assert 'current_atm_iv' in metrics, "metrics missing current_atm_iv"
    assert '30d_avg_iv' in metrics, "metrics missing 30d_avg_iv"
    assert 'iv_rank' in metrics, "metrics missing iv_rank"
    assert 'iv_percentile' in metrics, "metrics missing iv_percentile"
    
    assert 0.01 <= metrics['current_atm_iv'] <= 3.0, "current_atm_iv out of range"
    assert 0.01 <= metrics['30d_avg_iv'] <= 3.0, "30d_avg_iv out of range"
    
    # Validate explanation
    assert isinstance(result['explanation'], str), "explanation should be string"
    assert len(result['explanation']) > 10, "explanation should be meaningful"
    
    print("✅ All deterministic fixture schema validations passed!")


def test_options_forecast_health(client):
    """Test GET /api/options/health"""
    
    response = client.get('/api/options/health')
    
    assert response.status_code == 200
    data = response.get_json()
    
    assert data['status'] == 'ok'
    assert data['service'] == 'options_forecast_api'
    assert 'timestamp' in data
    
    print("✅ Health check passed!")


def test_options_forecast_blocks_live_mode(client):
    """Test that live mode (deterministic=False) is blocked"""
    
    # Temporarily disable OPTIONS_DETERMINISTIC
    old_val = os.environ.get('OPTIONS_DETERMINISTIC')
    os.environ['OPTIONS_DETERMINISTIC'] = '0'
    
    try:
        payload = {
            'ticker': 'AAPL',
            'deterministic': False  # Explicitly request live mode
        }
        
        response = client.post(
            '/api/options/forecast',
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Should return 403 Forbidden
        assert response.status_code == 403, f"Expected 403 for live mode, got {response.status_code}"
        
        data = response.get_json()
        assert data['error'] == True, "Expected error=True for blocked live mode"
        assert 'disabled during validation' in data['message'].lower(), "Expected validation message"
        
        print("✅ Live mode correctly blocked!")
        
    finally:
        # Restore env var
        if old_val:
            os.environ['OPTIONS_DETERMINISTIC'] = old_val
        else:
            os.environ.pop('OPTIONS_DETERMINISTIC', None)


if __name__ == '__main__':
    # Run tests manually
    import sys
    
    print("=" * 60)
    print("TESTING OPTIONS FORECAST API ENDPOINT")
    print("=" * 60)
    
    os.environ['OPTIONS_DETERMINISTIC'] = '1'
    app = create_app()
    app.server.config['TESTING'] = True
    
    with app.server.test_client() as test_client:
        print("\n1. Testing deterministic fixture...")
        test_options_forecast_deterministic(test_client)
        
        print("\n2. Testing health endpoint...")
        test_options_forecast_health(test_client)
        
        print("\n3. Testing live mode blocking...")
        test_options_forecast_blocks_live_mode(test_client)
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)
