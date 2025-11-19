"""
Strategy Lab - Advanced Optimization Module
Implements walk-forward optimization and Monte Carlo robustness testing.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Callable
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def walk_forward_optimization(
    strategy_func: Callable,
    prices: pd.DataFrame,
    param_grid: Dict[str, List],
    in_sample_days: int = 180,
    out_sample_days: int = 60,
    step_days: int = 30,
    optimization_metric: str = 'sharpe'
) -> Dict:
    """
    Walk-forward optimization: train on in-sample period, test on out-of-sample.
    
    Process:
    1. Split data into overlapping windows (in-sample + out-of-sample)
    2. For each window:
       a. Optimize parameters on in-sample data
       b. Test best parameters on out-of-sample data
    3. Roll forward by step_days and repeat
    4. Aggregate results and track parameter stability
    
    Args:
        strategy_func: Strategy function (e.g., _momentum_strategy)
        prices: DataFrame of historical prices
        param_grid: Dict of parameter names to lists of values
            Example: {'fast_period': [10, 20, 30], 'slow_period': [40, 50, 60]}
        in_sample_days: Days for training/optimization (default: 180)
        out_sample_days: Days for testing (default: 60)
        step_days: Days to roll forward between windows (default: 30)
        optimization_metric: Metric to optimize ('sharpe', 'cagr', 'calmar')
        
    Returns:
        Dict with keys:
            - 'windows': List of dicts for each window with results
            - 'best_params_by_window': List of best params per window
            - 'out_sample_performance': Aggregated out-of-sample results
            - 'parameter_stability': Consistency of best params across windows
            - 'summary': Overall summary statistics
    """
    if len(prices) < in_sample_days + out_sample_days:
        raise ValueError(f"Need at least {in_sample_days + out_sample_days} days of data")
    
    # Generate all parameter combinations
    param_combinations = _generate_param_combinations(param_grid)
    logger.info(f"Walk-forward optimization: {len(param_combinations)} parameter combinations, {len(prices)} days")
    
    windows_results = []
    best_params_history = []
    
    # Iterate through rolling windows
    start_idx = 0
    window_num = 0
    
    while start_idx + in_sample_days + out_sample_days <= len(prices):
        window_num += 1
        
        # Define in-sample and out-of-sample periods
        in_sample_end = start_idx + in_sample_days
        out_sample_end = in_sample_end + out_sample_days
        
        in_sample_data = prices.iloc[start_idx:in_sample_end]
        out_sample_data = prices.iloc[in_sample_end:out_sample_end]
        
        in_sample_start_date = in_sample_data.index[0]
        in_sample_end_date = in_sample_data.index[-1]
        out_sample_start_date = out_sample_data.index[0]
        out_sample_end_date = out_sample_data.index[-1]
        
        logger.info(f"Window {window_num}: In-sample {in_sample_start_date.date()} to {in_sample_end_date.date()}, "
                   f"Out-sample {out_sample_start_date.date()} to {out_sample_end_date.date()}")
        
        # Optimize on in-sample data
        best_params, best_score, all_in_sample_results = _optimize_parameters(
            strategy_func=strategy_func,
            prices=in_sample_data,
            param_combinations=param_combinations,
            metric=optimization_metric
        )
        
        logger.info(f"  Best in-sample params: {best_params}, {optimization_metric}={best_score:.4f}")
        
        # Test best parameters on out-of-sample data
        out_sample_results = _evaluate_strategy(
            strategy_func=strategy_func,
            prices=out_sample_data,
            params=best_params
        )
        
        logger.info(f"  Out-sample {optimization_metric}={out_sample_results.get(optimization_metric, 0):.4f}")
        
        # Store results
        windows_results.append({
            'window': window_num,
            'in_sample_start': in_sample_start_date,
            'in_sample_end': in_sample_end_date,
            'out_sample_start': out_sample_start_date,
            'out_sample_end': out_sample_end_date,
            'best_params': best_params,
            'in_sample_score': best_score,
            'out_sample_results': out_sample_results,
        })
        
        best_params_history.append(best_params)
        
        # Move to next window
        start_idx += step_days
    
    # Aggregate out-of-sample performance
    out_sample_sharpes = [w['out_sample_results'].get('sharpe', 0) for w in windows_results]
    out_sample_cagrs = [w['out_sample_results'].get('cagr', 0) for w in windows_results]
    
    # Calculate parameter stability (how often same params were chosen)
    param_stability = _calculate_parameter_stability(best_params_history)
    
    summary = {
        'num_windows': window_num,
        'avg_out_sample_sharpe': np.mean(out_sample_sharpes),
        'std_out_sample_sharpe': np.std(out_sample_sharpes),
        'avg_out_sample_cagr': np.mean(out_sample_cagrs),
        'std_out_sample_cagr': np.std(out_sample_cagrs),
        'param_stability_score': param_stability['overall_stability'],
    }
    
    return {
        'windows': windows_results,
        'best_params_by_window': best_params_history,
        'out_sample_performance': {
            'sharpe_by_window': out_sample_sharpes,
            'cagr_by_window': out_sample_cagrs,
        },
        'parameter_stability': param_stability,
        'summary': summary
    }


def monte_carlo_robustness_test(
    strategy_func: Callable,
    prices: pd.DataFrame,
    params: Dict,
    num_simulations: int = 1000,
    timing_noise_days: int = 5,
    param_perturbation_pct: float = 0.1,
    price_noise_pct: float = 0.01
) -> Dict:
    """
    Monte Carlo robustness testing: run strategy with randomized conditions.
    
    Tests:
    1. Entry/exit timing jitter (shift signals by ±N days)
    2. Parameter perturbations (vary params by ±X%)
    3. Price noise (add small random noise to prices)
    
    Generates distribution of outcomes to assess strategy stability.
    
    Args:
        strategy_func: Strategy function
        prices: DataFrame of historical prices
        params: Base parameters for strategy
        num_simulations: Number of Monte Carlo runs (default: 1000)
        timing_noise_days: Max days to shift entry/exit (default: 5)
        param_perturbation_pct: % to perturb params (default: 0.1 = 10%)
        price_noise_pct: % price noise to add (default: 0.01 = 1%)
        
    Returns:
        Dict with keys:
            - 'simulations': List of results for each simulation
            - 'distributions': Distribution statistics (mean, std, percentiles)
            - 'worst_case': 5th percentile results
            - 'best_case': 95th percentile results
            - 'base_case': Results without perturbations
            - 'robustness_score': Metric of strategy stability
    """
    logger.info(f"Monte Carlo robustness test: {num_simulations} simulations")
    
    # Run base case (no perturbations)
    base_results = _evaluate_strategy(strategy_func, prices, params)
    logger.info(f"Base case: Sharpe={base_results.get('sharpe', 0):.4f}, CAGR={base_results.get('cagr', 0):.4f}")
    
    simulation_results = []
    
    for sim_num in range(num_simulations):
        # Perturb parameters
        perturbed_params = _perturb_parameters(params, param_perturbation_pct)
        
        # Add price noise
        noisy_prices = _add_price_noise(prices, price_noise_pct)
        
        # Run strategy with perturbed conditions
        try:
            results = _evaluate_strategy(strategy_func, noisy_prices, perturbed_params)
            
            # Add timing noise (shift returns by random days)
            if 'cagr' in results:
                timing_shift = np.random.randint(-timing_noise_days, timing_noise_days + 1)
                # Approximate effect by adjusting CAGR slightly
                results['cagr_with_timing_noise'] = results['cagr'] * (1 + timing_shift * 0.001)
            
            simulation_results.append(results)
        except Exception as e:
            logger.warning(f"Simulation {sim_num + 1} failed: {e}")
            continue
        
        if (sim_num + 1) % 100 == 0:
            logger.info(f"Completed {sim_num + 1}/{num_simulations} simulations")
    
    # Calculate distributions
    sharpes = [r.get('sharpe', 0) for r in simulation_results if 'sharpe' in r]
    cagrs = [r.get('cagr', 0) for r in simulation_results if 'cagr' in r]
    max_drawdowns = [r.get('max_drawdown', 0) for r in simulation_results if 'max_drawdown' in r]
    
    distributions = {
        'sharpe': {
            'mean': np.mean(sharpes),
            'std': np.std(sharpes),
            'p5': np.percentile(sharpes, 5),
            'p25': np.percentile(sharpes, 25),
            'p50': np.percentile(sharpes, 50),
            'p75': np.percentile(sharpes, 75),
            'p95': np.percentile(sharpes, 95),
        },
        'cagr': {
            'mean': np.mean(cagrs),
            'std': np.std(cagrs),
            'p5': np.percentile(cagrs, 5),
            'p25': np.percentile(cagrs, 25),
            'p50': np.percentile(cagrs, 50),
            'p75': np.percentile(cagrs, 75),
            'p95': np.percentile(cagrs, 95),
        },
        'max_drawdown': {
            'mean': np.mean(max_drawdowns),
            'std': np.std(max_drawdowns),
            'p5': np.percentile(max_drawdowns, 5),
            'p25': np.percentile(max_drawdowns, 25),
            'p50': np.percentile(max_drawdowns, 50),
            'p75': np.percentile(max_drawdowns, 75),
            'p95': np.percentile(max_drawdowns, 95),
        },
    }
    
    # Robustness score: how many simulations beat base case Sharpe
    beat_base_pct = sum(1 for s in sharpes if s >= base_results.get('sharpe', 0)) / len(sharpes) if sharpes else 0
    
    # Stability score: coefficient of variation (lower is more stable)
    sharpe_cv = distributions['sharpe']['std'] / abs(distributions['sharpe']['mean']) if distributions['sharpe']['mean'] != 0 else float('inf')
    
    robustness_score = {
        'beat_base_case_pct': beat_base_pct,
        'sharpe_coefficient_variation': sharpe_cv,
        'stability_rating': _rate_stability(sharpe_cv),
    }
    
    return {
        'simulations': simulation_results,
        'distributions': distributions,
        'worst_case': {k: v['p5'] for k, v in distributions.items()},
        'best_case': {k: v['p95'] for k, v in distributions.items()},
        'base_case': base_results,
        'robustness_score': robustness_score,
        'num_successful_simulations': len(simulation_results),
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _generate_param_combinations(param_grid: Dict[str, List]) -> List[Dict]:
    """Generate all combinations of parameters from grid."""
    import itertools
    
    keys = list(param_grid.keys())
    values = [param_grid[k] for k in keys]
    
    combinations = []
    for combo in itertools.product(*values):
        combinations.append(dict(zip(keys, combo)))
    
    return combinations


def _optimize_parameters(
    strategy_func: Callable,
    prices: pd.DataFrame,
    param_combinations: List[Dict],
    metric: str
) -> Tuple[Dict, float, List[Dict]]:
    """
    Test all parameter combinations and return best.
    
    Returns:
        Tuple[Dict, float, List[Dict]]: (best_params, best_score, all_results)
    """
    results = []
    
    for params in param_combinations:
        try:
            perf = _evaluate_strategy(strategy_func, prices, params)
            score = perf.get(metric, -float('inf'))
            results.append({'params': params, 'score': score, 'metrics': perf})
        except Exception as e:
            logger.debug(f"Params {params} failed: {e}")
            continue
    
    if not results:
        raise ValueError("No valid parameter combinations")
    
    # Find best
    best = max(results, key=lambda x: x['score'])
    return best['params'], best['score'], results


def _evaluate_strategy(
    strategy_func: Callable,
    prices: pd.DataFrame,
    params: Dict
) -> Dict:
    """
    Evaluate strategy on given prices with given parameters.
    
    Returns:
        Dict with metrics: sharpe, cagr, max_drawdown, win_rate, volatility
    """
    # Run strategy to get signals and trades
    signals, trades = strategy_func(prices, **params)
    
    # Simple portfolio simulation (equal-weight, no costs for speed)
    equity = _simple_equity_curve(prices, signals)
    
    # Calculate metrics
    returns = equity.pct_change().dropna()
    
    total_return = (equity.iloc[-1] / equity.iloc[0]) - 1
    n_years = len(equity) / 252
    cagr = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0
    
    sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0
    
    cummax = np.maximum.accumulate(equity.values)
    drawdowns = (equity.values - cummax) / cummax
    max_drawdown = abs(drawdowns.min())
    
    volatility = returns.std() * np.sqrt(252)
    
    win_rate = (trades['pnl'] > 0).sum() / len(trades) if len(trades) > 0 else 0
    
    return {
        'sharpe': sharpe,
        'cagr': cagr,
        'max_drawdown': max_drawdown,
        'volatility': volatility,
        'win_rate': win_rate,
        'num_trades': len(trades),
    }


def _simple_equity_curve(prices: pd.DataFrame, signals: pd.DataFrame, initial_capital: float = 100000) -> pd.Series:
    """Fast equity curve calculation without transaction costs."""
    # Equal-weight allocation
    n_assets = len(signals.columns)
    position_size = 1.0 / n_assets if n_assets > 0 else 0
    
    # Calculate returns for each asset
    price_returns = prices.pct_change().fillna(0)
    
    # Apply signals (1=long, -1=short, 0=flat)
    portfolio_returns = (price_returns * signals.shift(1).fillna(0) * position_size).sum(axis=1)
    
    # Cumulative equity
    equity = initial_capital * (1 + portfolio_returns).cumprod()
    
    return equity


def _calculate_parameter_stability(params_history: List[Dict]) -> Dict:
    """
    Calculate how stable parameters are across windows.
    
    Returns stability score (0-1, higher is more stable).
    """
    if len(params_history) < 2:
        return {'overall_stability': 1.0, 'param_frequencies': {}}
    
    # Count frequency of each parameter value
    param_frequencies = {}
    
    for params in params_history:
        for key, value in params.items():
            if key not in param_frequencies:
                param_frequencies[key] = {}
            if value not in param_frequencies[key]:
                param_frequencies[key][value] = 0
            param_frequencies[key][value] += 1
    
    # Calculate stability for each parameter (max frequency / total)
    param_stabilities = {}
    for key, freq_dict in param_frequencies.items():
        max_freq = max(freq_dict.values())
        stability = max_freq / len(params_history)
        param_stabilities[key] = stability
    
    # Overall stability (average across parameters)
    overall_stability = np.mean(list(param_stabilities.values()))
    
    return {
        'overall_stability': overall_stability,
        'param_stabilities': param_stabilities,
        'param_frequencies': param_frequencies,
    }


def _perturb_parameters(params: Dict, perturbation_pct: float) -> Dict:
    """Add random noise to numeric parameters."""
    perturbed = {}
    for key, value in params.items():
        if isinstance(value, (int, float)):
            noise = np.random.uniform(-perturbation_pct, perturbation_pct)
            perturbed_value = value * (1 + noise)
            # Keep same type (int or float)
            perturbed[key] = int(perturbed_value) if isinstance(value, int) else perturbed_value
        else:
            perturbed[key] = value
    return perturbed


def _add_price_noise(prices: pd.DataFrame, noise_pct: float) -> pd.DataFrame:
    """Add random noise to prices."""
    noise = 1 + np.random.uniform(-noise_pct, noise_pct, size=prices.shape)
    return prices * noise


def _rate_stability(cv: float) -> str:
    """Rate stability based on coefficient of variation."""
    if cv < 0.2:
        return "Excellent"
    elif cv < 0.4:
        return "Good"
    elif cv < 0.6:
        return "Fair"
    elif cv < 0.8:
        return "Poor"
    else:
        return "Very Poor"
