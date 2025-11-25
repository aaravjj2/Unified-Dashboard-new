from functools import wraps
import dash

"""
Lightweight guard utilities to wrap Dash callback registration so that
callbacks that receive None for expected inputs/states early-exit by
raising PreventUpdate instead of causing server-side 500 errors.

Usage:
    from financial_dashboard.utils.callback_guards import install_guard, uninstall_guard
    orig = install_guard(app)
    try:
        # import or call functions that use @app.callback decorators
        register_callbacks(app)
    finally:
        uninstall_guard(app)
"""


def install_guard(app):
    """Monkeypatch `app.callback` to wrap registered callback functions
    with a simple guard that prevents execution when any positional
    argument is None. Returns the original `app.callback` so it can be
    restored.
    """
    if hasattr(app, '_callback_guard_installed') and app._callback_guard_installed:
        return getattr(app, '_original_callback', app.callback)

    original_callback = app.callback

    def guarded_callback(*cb_args, **cb_kwargs):
        def decorator(func):
            @wraps(func)
            def wrapper(*f_args, **f_kwargs):
                # Defensive: if any required positional arg is None,
                # do not run the callback and prevent update instead.
                try:
                    if any(a is None for a in f_args):
                        raise dash.exceptions.PreventUpdate()
                except Exception:
                    # If dash isn't available for PreventUpdate, raise
                    raise
                return func(*f_args, **f_kwargs)

            # Register the wrapped function with the original decorator
            return original_callback(*cb_args, **cb_kwargs)(wrapper)

        return decorator

    # Attach markers so install/uninstall are idempotent
    app._original_callback = original_callback
    app.callback = guarded_callback
    app._callback_guard_installed = True
    return original_callback


def uninstall_guard(app):
    """Restore the original `app.callback` if previously installed."""
    if hasattr(app, '_callback_guard_installed') and app._callback_guard_installed:
        try:
            app.callback = getattr(app, '_original_callback', app.callback)
        except Exception:
            pass
        finally:
            app._callback_guard_installed = False
            if hasattr(app, '_original_callback'):
                delattr(app, '_original_callback')
