"""
Scenario simulator for "What-If" analysis of economic events.
"""

import numpy as np
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class ScenarioSimulator:
    """Simulate market reactions to economic events."""
    
    # Predefined scenario templates with impact coefficients
    SCENARIOS = {
        'fed_rate_cut': {
            'name': 'Fed Rate Cut',
            'description': 'Federal Reserve cuts interest rates',
            'param_name': 'Rate Change (bps)',
            'param_range': (-50, 0),
            'param_default': -25,
            'impact_coefficient': 0.015,  # 1.5% market impact per 100bps
        },
        'fed_rate_hike': {
            'name': 'Fed Rate Hike',
            'description': 'Federal Reserve raises interest rates',
            'param_name': 'Rate Change (bps)',
            'param_range': (0, 50),
            'param_default': 25,
            'impact_coefficient': -0.012,  # -1.2% market impact per 100bps
        },
        'vix_spike': {
            'name': 'VIX Spike',
            'description': 'Volatility index increases sharply',
            'param_name': 'VIX Increase (points)',
            'param_range': (5, 50),
            'param_default': 15,
            'impact_coefficient': -0.008,  # -0.8% per VIX point
        },
        'earnings_beat': {
            'name': 'Earnings Beat',
            'description': 'Company beats earnings expectations',
            'param_name': 'Beat Percentage (%)',
            'param_range': (0, 30),
            'param_default': 10,
            'impact_coefficient': 0.025,  # 2.5% per 10% beat
        },
        'earnings_miss': {
            'name': 'Earnings Miss',
            'description': 'Company misses earnings expectations',
            'param_name': 'Miss Percentage (%)',
            'param_range': (0, 30),
            'param_default': 10,
            'impact_coefficient': -0.030,  # -3.0% per 10% miss
        },
        'sector_rotation': {
            'name': 'Sector Rotation',
            'description': 'Capital flows from growth to value stocks',
            'param_name': 'Rotation Intensity (%)',
            'param_range': (0, 100),
            'param_default': 50,
            'impact_coefficient': -0.005,  # Varies by sector
        },
    }
    
    @classmethod
    def apply_scenario(cls, baseline_forecast: List[float], scenario_type: str, 
                      param_value: float, decay_rate: float = 0.9) -> Dict:
        """
        Apply scenario shock to baseline forecast.
        
        Args:
            baseline_forecast: Original forecast values
            scenario_type: Type of scenario (key from SCENARIOS)
            param_value: Scenario parameter value (e.g., -25 for 25bps cut)
            decay_rate: How quickly the impact decays over time (0-1)
            
        Returns:
            Dict with 'adjusted_forecast', 'impact', 'scenario_info'
        """
        if scenario_type not in cls.SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario_type}")
        
        scenario = cls.SCENARIOS[scenario_type]
        
        # Calculate initial impact
        impact_coefficient = scenario['impact_coefficient']
        initial_impact = param_value * impact_coefficient / 100  # Convert to decimal
        
        # Apply decaying impact over forecast horizon
        horizon = len(baseline_forecast)
        impacts = []
        adjusted_forecast = []
        
        for i, baseline_value in enumerate(baseline_forecast):
            # Impact decays exponentially
            time_decay = decay_rate ** i
            current_impact = initial_impact * time_decay
            
            # Apply impact to baseline
            adjusted_value = baseline_value * (1 + current_impact)
            
            impacts.append(current_impact * 100)  # Convert to percentage
            adjusted_forecast.append(adjusted_value)
        
        return {
            'adjusted_forecast': adjusted_forecast,
            'impact_pct': impacts,
            'scenario_info': {
                'type': scenario_type,
                'name': scenario['name'],
                'description': scenario['description'],
                'parameter': param_value,
                'initial_impact_pct': initial_impact * 100,
            }
        }
    
    @classmethod
    def get_scenario_options(cls) -> List[Dict]:
        """Get list of available scenarios for UI dropdown."""
        return [
            {
                'label': f"{info['name']} - {info['description']}",
                'value': key
            }
            for key, info in cls.SCENARIOS.items()
        ]
    
    @classmethod
    def get_scenario_params(cls, scenario_type: str) -> Dict:
        """Get parameter configuration for a specific scenario."""
        if scenario_type not in cls.SCENARIOS:
            return {}
        
        scenario = cls.SCENARIOS[scenario_type]
        return {
            'name': scenario['param_name'],
            'min': scenario['param_range'][0],
            'max': scenario['param_range'][1],
            'default': scenario['param_default'],
        }
