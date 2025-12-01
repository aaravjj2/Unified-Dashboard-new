#!/usr/bin/env python3
"""
Sentry Integration for Phase 24-25 Error Tracking
"""

import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
import os

def init_sentry():
    """Initialize Sentry error tracking"""
    
    sentry_dsn = os.getenv('SENTRY_DSN')
    if not sentry_dsn:
        print("⚠️ SENTRY_DSN not configured - skipping Sentry initialization")
        return False
    
    sentry_logging = LoggingIntegration(
        level=logging.INFO,        # Capture info and above as breadcrumbs
        event_level=logging.ERROR  # Send errors as events
    )
    
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[
            FlaskIntegration(transaction_style='endpoint'),
            sentry_logging,
        ],
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        environment=os.getenv('ENVIRONMENT', 'development'),
        release=os.getenv('SENTRY_RELEASE', 'phase-24-25-fix'),
        before_send=filter_errors,
    )
    
    print("✅ Sentry initialized successfully")
    return True

def filter_errors(event, hint):
    """Filter out noise from Sentry events"""
    
    # Filter out known non-critical errors
    if 'exc_info' in hint:
        exc_type, exc_value, tb = hint['exc_info']
        
        # Skip certain error types
        if exc_type.__name__ in ['KeyboardInterrupt', 'SystemExit']:
            return None
    
    # Add custom tags for Phase 24-25 tracking
    event.setdefault('tags', {})['phase'] = '24-25-critical-fix'
    
    return event

def capture_react_error(error_message, component_stack=None):
    """Capture React errors specifically"""
    
    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("error_type", "react_error")
        scope.set_tag("phase", "24-25-fix")
        
        if component_stack:
            scope.set_context("react_component_stack", {
                "stack": component_stack
            })
        
        sentry_sdk.capture_message(f"React Error: {error_message}", level="error")

def capture_callback_error(callback_name, error_details):
    """Capture callback-specific errors"""
    
    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("error_type", "callback_error")
        scope.set_tag("callback_name", callback_name)
        scope.set_tag("phase", "24-25-fix")
        
        scope.set_context("callback_details", error_details)
        
        sentry_sdk.capture_message(f"Callback Error in {callback_name}", level="error")

# Usage in dashboard application:
# from sentry_integration import init_sentry, capture_react_error, capture_callback_error
# init_sentry()
