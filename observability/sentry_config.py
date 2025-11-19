"""
Sentry Exception Tracking Configuration
Phase 22: Observability, Monitoring, and Optional Enhancements

Provides centralized Sentry initialization and exception capture utilities.
"""

import os
import logging
from typing import Dict, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)

# Sentry initialization flag
_sentry_initialized = False

def init_sentry() -> bool:
    """
    Initialize Sentry SDK for exception tracking.
    
    Returns:
        bool: True if Sentry initialized successfully, False otherwise
    """
    global _sentry_initialized
    
    if _sentry_initialized:
        logger.info("✅ Sentry already initialized")
        return True
    
    sentry_dsn = os.getenv('SENTRY_DSN')
    
    if not sentry_dsn:
        logger.warning("⚠️ SENTRY_DSN not configured - exception tracking disabled")
        return False
    
    try:
        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        
        # Configure Sentry
        # Build integrations list dynamically to avoid hard failures if optional
        # integrations are not available in a minimal runtime.
        integrations = [
            FlaskIntegration(),
            LoggingIntegration(
                level=logging.INFO,
                event_level=logging.ERROR
            )
        ]

        # Add Starlette/ASGI integration when available (helps FastAPI/Uvicorn apps)
        try:
            from sentry_sdk.integrations.starlette import StarletteIntegration
            integrations.append(StarletteIntegration())
        except Exception:
            # starlette integration not required; continue gracefully
            pass

        # Allow the runtime to provide a release string (useful in Docker)
        release = os.getenv('SENTRY_RELEASE') or os.getenv('GIT_COMMIT')

        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=integrations,
            environment=os.getenv('DASH_ENV', 'production'),
            release=release,
            traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1')),
            profiles_sample_rate=float(os.getenv('SENTRY_PROFILES_SAMPLE_RATE', '0.1')),
            send_default_pii=False,
            max_breadcrumbs=50,
            attach_stacktrace=True
        )
        
        _sentry_initialized = True
        logger.info("✅ Sentry initialized successfully")
        return True
        
    except ImportError:
        logger.warning("⚠️ sentry-sdk not installed - exception tracking disabled")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to initialize Sentry: {e}")
        return False


def capture_exception(
    error: Exception,
    context: str,
    extra: Optional[Dict[str, Any]] = None,
    level: str = 'error'
) -> None:
    """
    Capture exception with context for Sentry.
    
    Args:
        error: The exception to capture
        context: Context string (e.g., 'azure_ml_callback')
        extra: Additional context data
        level: Severity level ('error', 'warning', 'info')
    """
    try:
        import sentry_sdk
        
        with sentry_sdk.push_scope() as scope:
            # Add context tags
            scope.set_tag('context', context)
            scope.set_tag('environment', os.getenv('DASH_ENV', 'production'))
            
            # Add extra context
            if extra:
                for key, value in extra.items():
                    scope.set_extra(key, value)
            
            # Set level
            scope.level = level
            
            # Capture exception
            sentry_sdk.capture_exception(error)
            
        logger.error(f"❌ Exception captured in {context}: {error}")
        
    except ImportError:
        logger.error(f"❌ Exception in {context} (Sentry not available): {error}")
    except Exception as e:
        logger.error(f"❌ Failed to capture exception in Sentry: {e}")


def capture_message(
    message: str,
    context: str,
    level: str = 'info',
    extra: Optional[Dict[str, Any]] = None
) -> None:
    """
    Capture message for Sentry (non-exception events).
    
    Args:
        message: The message to capture
        context: Context string
        level: Severity level ('error', 'warning', 'info')
        extra: Additional context data
    """
    try:
        import sentry_sdk
        
        with sentry_sdk.push_scope() as scope:
            scope.set_tag('context', context)
            scope.set_tag('environment', os.getenv('DASH_ENV', 'production'))
            
            if extra:
                for key, value in extra.items():
                    scope.set_extra(key, value)
            
            scope.level = level
            sentry_sdk.capture_message(message)
            
        logger.info(f"📊 Message captured in {context}: {message}")
        
    except ImportError:
        logger.info(f"📊 Message in {context} (Sentry not available): {message}")
    except Exception as e:
        logger.error(f"❌ Failed to capture message in Sentry: {e}")


def sentry_trace(context: str):
    """
    Decorator to automatically capture exceptions in Sentry.
    
    Usage:
        @sentry_trace('azure_ml_callback')
        def my_callback():
            # callback code
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                capture_exception(
                    e,
                    context=context,
                    extra={
                        'function': func.__name__,
                        'args': str(args)[:200],
                        'kwargs': str(kwargs)[:200]
                    }
                )
                raise
        return wrapper
    return decorator


def add_breadcrumb(
    message: str,
    category: str,
    level: str = 'info',
    data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Add breadcrumb for Sentry context trail.
    
    Args:
        message: Breadcrumb message
        category: Category (e.g., 'callback', 'api', 'database')
        level: Severity level
        data: Additional data
    """
    try:
        import sentry_sdk
        
        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level,
            data=data or {}
        )
        
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"⚠️ Failed to add breadcrumb: {e}")


def set_user_context(user_id: str, username: Optional[str] = None) -> None:
    """
    Set user context for Sentry.
    
    Args:
        user_id: User identifier
        username: Optional username
    """
    try:
        import sentry_sdk
        
        sentry_sdk.set_user({
            'id': user_id,
            'username': username
        })
        
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"⚠️ Failed to set user context: {e}")


# Initialize Sentry on module import
init_sentry()
