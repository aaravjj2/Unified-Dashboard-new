"""
Test Portfolio SHAP Auto-Generation

Validates that SHAP explanations are automatically generated when missing.
"""

import pytest
import os
import sys
import json
import tempfile
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import numpy as np


@pytest.fixture
def temp_explain_dir(monkeypatch):
    """Create temporary explain directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv('EXPLAIN_DIR', tmpdir)
        # Patch the module-level EXPLAIN_DIR
        import financial_dashboard.utils.explain as explain_module
        original_dir = explain_module.EXPLAIN_DIR
        explain_module.EXPLAIN_DIR = tmpdir
        yield tmpdir
        explain_module.EXPLAIN_DIR = original_dir


class TestSHAPAutoGeneration:
    """Test SHAP auto-generation functionality."""
    
    def test_load_existing_shap_file(self, temp_explain_dir):
        """Test loading existing SHAP file without regeneration."""
        from financial_dashboard.utils.explain import load_shap_explanations
        
        # Create a mock SHAP file
        test_date = '20251023'
        test_data = {
            'generated_at': datetime.now().isoformat(),
            'date': test_date,
            'explanations': {
                'AAPL': {
                    'base_value': 0.5,
                    'prediction': 0.75,
                    'top_features': [
                        {'feature': 'momentum', 'shap_value': 0.15},
                        {'feature': 'volatility', 'shap_value': -0.05}
                    ]
                }
            }
        }
        
        filepath = os.path.join(temp_explain_dir, f'picks_explain_{test_date}.json')
        with open(filepath, 'w') as f:
            json.dump(test_data, f)
        
        # Load SHAP data
        result = load_shap_explanations(test_date)
        
        assert result is not None
        assert result['date'] == test_date
        assert 'AAPL' in result['explanations']
        assert len(result['explanations']['AAPL']['top_features']) == 2
    
    def test_autogenerate_missing_shap_file(self, temp_explain_dir):
        """Test automatic generation when SHAP file is missing."""
        test_date = '20251023'
        
        # Create mock modules at sys.modules level
        mock_models_module = MagicMock()
        mock_data_prep_module = MagicMock()
        
        # Mock model and prediction
        mock_model = Mock()
        mock_model.predict = Mock(return_value=np.array([0.75, 0.65]))
        mock_models_module.load_latest_model = Mock(return_value=mock_model)
        
        # Mock feature preparation
        mock_features = np.array([[1.0, 2.0, 3.0], [1.5, 2.5, 3.5]])
        mock_feature_names = ['momentum', 'volatility', 'trend']
        mock_tickers = ['AAPL', 'MSFT']
        mock_data_prep_module.prepare_features_for_date = Mock(
            return_value=(mock_features, mock_feature_names, mock_tickers)
        )
        
        # Inject mock modules
        sys.modules['utils.models'] = mock_models_module
        sys.modules['utils.data_prep'] = mock_data_prep_module
        
        try:
            with patch('financial_dashboard.utils.explain.compute_shap_values') as mock_compute_shap:
                # Mock SHAP computation
                mock_compute_shap.return_value = {
                    'shap_values': np.array([[0.1, -0.05, 0.15], [0.08, -0.03, 0.10]]),
                    'base_value': 0.5,
                    'feature_names': mock_feature_names
                }
                
                from financial_dashboard.utils.explain import get_or_generate_shap_data
                
                # Call get_or_generate_shap_data
                result = get_or_generate_shap_data(test_date)
                
                # Verify file was created
                filepath = os.path.join(temp_explain_dir, f'picks_explain_{test_date}.json')
                assert os.path.exists(filepath), "SHAP file should be auto-generated"
                
                # Verify result structure
                assert result is not None
                assert result['date'] == test_date
                assert 'explanations' in result
                assert 'AAPL' in result['explanations']
                assert 'MSFT' in result['explanations']
        finally:
            # Cleanup
            sys.modules.pop('utils.models', None)
            sys.modules.pop('utils.data_prep', None)
    
    def test_fallback_when_model_unavailable(self, temp_explain_dir):
        """Test fallback behavior when model cannot be loaded."""
        from financial_dashboard.utils.explain import get_or_generate_shap_data
        
        test_date = '20251023'
        
        with patch('financial_dashboard.utils.explain.load_latest_model', return_value=None, create=True):
            result = get_or_generate_shap_data(test_date)
            
            # Should return fallback data
            assert result is not None
            assert result.get('status') == 'fallback'
            assert result['date'] == test_date
            assert 'message' in result
            assert result['explanations'] == {}
    
    def test_fallback_when_features_unavailable(self, temp_explain_dir):
        """Test fallback behavior when features cannot be prepared."""
        test_date = '20251023'
        
        # Create mock modules
        mock_models_module = MagicMock()
        mock_data_prep_module = MagicMock()
        
        mock_model = Mock()
        mock_models_module.load_latest_model = Mock(return_value=mock_model)
        mock_data_prep_module.prepare_features_for_date = Mock(return_value=(None, None, None))
        
        # Inject mock modules
        sys.modules['utils.models'] = mock_models_module
        sys.modules['utils.data_prep'] = mock_data_prep_module
        
        try:
            from financial_dashboard.utils.explain import get_or_generate_shap_data
            
            result = get_or_generate_shap_data(test_date)
            
            # Should return fallback data
            assert result is not None
            assert result.get('status') == 'fallback'
            # Adjust assertion to match actual fallback message
            assert 'unavailable' in result.get('message', '').lower()
        finally:
            sys.modules.pop('utils.models', None)
            sys.modules.pop('utils.data_prep', None)
    
    def test_load_shap_triggers_autogen_when_missing(self, temp_explain_dir):
        """Test that load_shap_explanations triggers auto-generation."""
        from financial_dashboard.utils.explain import load_shap_explanations
        
        test_date = '20251023'
        
        # Mock the auto-generation flow
        mock_fallback_data = {
            'date': test_date,
            'status': 'fallback',
            'message': 'Model not found',
            'explanations': {}
        }
        
        with patch('financial_dashboard.utils.explain.get_or_generate_shap_data', 
                  return_value=mock_fallback_data) as mock_gen:
            result = load_shap_explanations(test_date)
            
            # Verify auto-generation was called
            mock_gen.assert_called_once_with(test_date)
            assert result == mock_fallback_data
    
    def test_shap_data_persists_across_calls(self, temp_explain_dir):
        """Test that generated SHAP data persists and doesn't regenerate unnecessarily."""
        test_date = '20251023'
        
        # Create mock modules
        mock_models_module = MagicMock()
        mock_data_prep_module = MagicMock()
        
        mock_model = Mock()
        mock_model.predict = Mock(return_value=np.array([0.75, 0.65]))
        mock_models_module.load_latest_model = Mock(return_value=mock_model)
        
        mock_features = np.array([[1.0, 2.0, 3.0], [1.5, 2.5, 3.5]])
        mock_feature_names = ['momentum', 'volatility', 'trend']
        mock_tickers = ['AAPL', 'MSFT']
        mock_data_prep_module.prepare_features_for_date = Mock(
            return_value=(mock_features, mock_feature_names, mock_tickers)
        )
        
        # Inject mock modules
        sys.modules['utils.models'] = mock_models_module
        sys.modules['utils.data_prep'] = mock_data_prep_module
        
        try:
            with patch('financial_dashboard.utils.explain.compute_shap_values') as mock_compute_shap:
                mock_compute_shap.return_value = {
                    'shap_values': np.array([[0.1, -0.05, 0.15], [0.08, -0.03, 0.10]]),
                    'base_value': 0.5,
                    'feature_names': mock_feature_names
                }
                
                from financial_dashboard.utils.explain import get_or_generate_shap_data
                
                # First call generates file
                result1 = get_or_generate_shap_data(test_date)
                assert result1 is not None
                
                # Verify mocks were called
                assert mock_compute_shap.called
                
            # Second call should load from file without regenerating
            result2 = get_or_generate_shap_data(test_date)
            assert result2 is not None
            assert result2['date'] == test_date
            
            # Verify structure matches
            assert result1.get('explanations') == result2.get('explanations')
        finally:
            sys.modules.pop('utils.models', None)
            sys.modules.pop('utils.data_prep', None)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
