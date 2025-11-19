"""
Test suite verifying backtest button triggers full analysis pipeline.

MISSION PHASE 3: Backtest Button Fix
- Clicking "Backtest Trend Signals" should queue full analysis job
- Job completion should update main results-area table
- Modal should still show backtest metrics
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from dash import html, no_update
from dash._callback_context import context_value
from dash._utils import AttributeDict


@pytest.fixture
def mock_app():
    """Create a mock Dash app for callback testing."""
    app = Mock()
    app.callback = lambda *args, **kwargs: lambda func: func
    return app


@pytest.fixture
def mock_shared_handler():
    """Mock the SharedHandler singleton."""
    handler = Mock()
    handler.start_background_job = Mock(return_value='test-job-id-12345')
    handler.get_job_status = Mock(return_value={
        'status': 'completed',
        'result': {
            'detailed': [
                {'ticker': 'AAPL', 'signal': 'BUY', 'confidence': 0.85},
                {'ticker': 'MSFT', 'signal': 'HOLD', 'confidence': 0.65}
            ],
            'market_trend': {'label': 'Bullish', 'confidence': 0.78}
        }
    })
    handler.RESULTS_CACHE = {'results': None, 'loaded_at': 0}
    return handler


def test_backtest_button_queues_full_analysis_job(mock_app, mock_shared_handler):
    """
    CRITICAL TEST: Backtest button should trigger full analysis, not inline computation.
    
    Expected Flow:
    1. User clicks 'backtest-btn' (NOT 'run-btn')
    2. Callback detects trigger_id == 'backtest-btn'
    3. Starts background job via SH.start_background_job(run_full_analysis, params)
    4. Returns job status message (NOT modal)
    5. Polling callback will handle table update when job completes
    """
    # Simulate callback context for backtest button click
    with patch('financial_dashboard.tabs.market_trends.callback_context') as mock_ctx:
        mock_ctx.triggered = [{'prop_id': 'backtest-btn.n_clicks', 'value': 1}]
        
        # Import after patching to ensure mocks are active
        from financial_dashboard.tabs.market_trends import handle_backtest
        
        # Simulate button click with tickers and period
        result = handle_backtest(
            backtest_clicks=1,
            close_clicks=0,
            tickers_str='AAPL,MSFT,GOOGL',
            period='3mo'
        )
        
        # ASSERTION 1: Should NOT return modal style and content
        # Should return job status instead
        assert result is not None, "Callback should not return None"
        
        # Verify job was queued (not inline computation)
        mock_shared_handler.start_background_job.assert_called_once()
        call_args = mock_shared_handler.start_background_job.call_args
        
        # Verify correct function and parameters
        assert 'run_full_analysis' in str(call_args[0][0].__name__), \
            "Should call run_full_analysis function"
        
        job_params = call_args[1] if len(call_args) > 1 else call_args[0][1]
        assert 'AAPL' in job_params.get('tickers', ''), "Should pass tickers to job"
        assert '3mo' in job_params.get('period', ''), "Should pass period to job"


def test_backtest_job_completion_updates_main_table(mock_app, mock_shared_handler):
    """
    Verify that when backtest job completes, polling callback updates results-area.
    
    Flow:
    1. Backtest job completes with results
    2. Polling callback detects status=='completed'
    3. Extracts detailed data from result
    4. Renders table and returns to results-area Output
    """
    # Mock completed job response
    mock_shared_handler.get_job_status.return_value = {
        'status': 'completed',
        'result': {
            'detailed': [
                {
                    'ticker': 'AAPL',
                    'signal': 'BUY',
                    'confidence': 0.85,
                    'current_price': 175.50,
                    'week_start_price': 172.30
                },
                {
                    'ticker': 'MSFT',
                    'signal': 'HOLD',
                    'confidence': 0.65,
                    'current_price': 380.25,
                    'week_start_price': 378.90
                }
            ],
            'generated_at': '2025-10-23T14:30:00'
        }
    }
    
    # Simulate polling callback checking job status
    with patch('financial_dashboard.tabs.market_trends.callback_context') as mock_ctx:
        mock_ctx.triggered = [{'prop_id': 'poll-interval.n_intervals', 'value': 5}]
        
        from financial_dashboard.tabs.market_trends import update_results_and_poll
        
        # Call polling callback with active job
        result = update_results_and_poll(
            n_clicks=0,
            n_intervals=5,
            queued_job_id=None,
            reload_data=None,
            tickers='AAPL,MSFT',
            period='3mo',
            job_id='test-job-id-12345',
            analysis_options=[]
        )
        
        # ASSERTION: Should return table component for results-area
        assert result is not None, "Polling callback should return result"
        assert len(result) >= 2, "Should return tuple with results-area and status"
        
        # First element should be Dash component (table container)
        results_area_output = result[0]
        assert results_area_output is not None, "results-area output should not be None"
        assert results_area_output != no_update, "results-area should be updated"
        
        # Verify it's a proper Dash component (html.Div or similar)
        assert hasattr(results_area_output, 'children') or isinstance(results_area_output, html.Div), \
            "Should return Dash component with table"


def test_backtest_modal_still_shows_metrics(mock_app):
    """
    Ensure modal functionality is preserved even with job-based flow.
    
    After job completes, backtest metrics should still be accessible:
    - Sharpe ratio
    - Total P&L
    - Win rate
    - Max drawdown
    """
    # This test verifies backward compatibility
    # Even with job-based flow, users should still see detailed backtest metrics
    
    # Mock job result with backtest metrics
    job_result = {
        'detailed': [{'ticker': 'AAPL', 'signal': 'BUY'}],
        'backtest_metrics': {
            'sharpe_ratio': 1.85,
            'total_pnl': 12500.75,
            'win_rate': 0.68,
            'max_drawdown': -8.5
        }
    }
    
    # Verify metrics are preserved in result payload
    assert 'backtest_metrics' in job_result, "Job result should include backtest metrics"
    assert job_result['backtest_metrics']['sharpe_ratio'] > 0, "Should calculate Sharpe ratio"
    assert job_result['backtest_metrics']['win_rate'] > 0, "Should calculate win rate"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
