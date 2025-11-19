#!/usr/bin/env python3
"""
Datadog Integration for Phase 24-25 Metrics and Monitoring
"""

import os
import time
from datadog import initialize, statsd
import logging

logger = logging.getLogger(__name__)

class DatadogMetrics:
    def __init__(self):
        self.api_key = os.getenv('DATADOG_API_KEY')
        self.app_key = os.getenv('DATADOG_APP_KEY')
        self.service_name = 'financial-dashboard'
        self.environment = os.getenv('ENVIRONMENT', 'development')
        
        if self.api_key:
            self.init_datadog()
        else:
            logger.warning("DATADOG_API_KEY not configured - metrics will be logged only")
    
    def init_datadog(self):
        """Initialize Datadog"""
        try:
            options = {
                'api_key': self.api_key,
                'app_key': self.app_key
            }
            
            initialize(**options)
            
            # Configure StatsD
            statsd.host = os.getenv('DATADOG_HOST', 'localhost')
            statsd.port = int(os.getenv('DATADOG_PORT', 8125))
            
            logger.info("✅ Datadog initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Datadog initialization failed: {e}")
    
    def track_callback_performance(self, callback_name, execution_time, success=True):
        """Track callback performance metrics"""
        
        tags = [
            f'callback:{callback_name}',
            f'service:{self.service_name}',
            f'environment:{self.environment}',
            f'phase:24-25-fix',
            f'success:{success}'
        ]
        
        try:
            # Track execution time
            statsd.histogram('dashboard.callback.execution_time', execution_time, tags=tags)
            
            # Track callback invocation count
            statsd.increment('dashboard.callback.invocations', tags=tags)
            
            # Track success/failure rate
            if success:
                statsd.increment('dashboard.callback.success', tags=tags)
            else:
                statsd.increment('dashboard.callback.errors', tags=tags)
                
            logger.debug(f"📊 Tracked callback {callback_name}: {execution_time}ms, success={success}")
            
        except Exception as e:
            logger.error(f"❌ Failed to track callback metrics: {e}")
    
    def track_react_errors(self, error_type, component_name=None):
        """Track React errors"""
        
        tags = [
            f'error_type:{error_type}',
            f'service:{self.service_name}',
            f'environment:{self.environment}',
            f'phase:24-25-fix'
        ]
        
        if component_name:
            tags.append(f'component:{component_name}')
        
        try:
            statsd.increment('dashboard.react.errors', tags=tags)
            logger.debug(f"📊 Tracked React error: {error_type}")
            
        except Exception as e:
            logger.error(f"❌ Failed to track React error: {e}")
    
    def track_ui_interactions(self, interaction_type, element_id, success=True):
        """Track UI interaction metrics"""
        
        tags = [
            f'interaction:{interaction_type}',
            f'element:{element_id}',
            f'service:{self.service_name}',
            f'environment:{self.environment}',
            f'phase:24-25-fix',
            f'success:{success}'
        ]
        
        try:
            statsd.increment('dashboard.ui.interactions', tags=tags)
            
            if success:
                statsd.increment('dashboard.ui.interactions.success', tags=tags)
            else:
                statsd.increment('dashboard.ui.interactions.failures', tags=tags)
                
            logger.debug(f"📊 Tracked UI interaction: {interaction_type} on {element_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to track UI interaction: {e}")
    
    def track_page_load_time(self, page_name, load_time):
        """Track page load performance"""
        
        tags = [
            f'page:{page_name}',
            f'service:{self.service_name}',
            f'environment:{self.environment}',
            f'phase:24-25-fix'
        ]
        
        try:
            statsd.histogram('dashboard.page.load_time', load_time, tags=tags)
            logger.debug(f"📊 Tracked page load: {page_name} in {load_time}ms")
            
        except Exception as e:
            logger.error(f"❌ Failed to track page load time: {e}")

# Decorator for automatic callback tracking
def track_callback(callback_name):
    """Decorator to automatically track callback performance"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                raise
            finally:
                execution_time = (time.time() - start_time) * 1000  # Convert to ms
                
                # Track metrics
                metrics = DatadogMetrics()
                metrics.track_callback_performance(callback_name, execution_time, success)
        
        return wrapper
    return decorator

# Usage examples:
# metrics = DatadogMetrics()
# metrics.track_callback_performance('portfolio_update', 150.5, True)
# metrics.track_react_errors('error_31', 'PortfolioComponent')
# 
# @track_callback('portfolio_update')
# def portfolio_callback():
#     # Your callback code here
#     pass
