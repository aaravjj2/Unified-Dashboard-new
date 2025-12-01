"""
Callback Registration Instrumentation for Duplicate Detection

This module wraps Dash's callback registration to trace all callback
registrations with caller context (file, line, function).
"""
import inspect
import json
import traceback
from datetime import datetime
from pathlib import Path


class CallbackRegistrationTracer:
    """Trace all callback registrations with detailed context."""
    
    def __init__(self, log_path='reports/duplicates_fix/diagnostics/callback_registration_trace.log'):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.registrations = []
        self.seen_outputs = {}  # Track duplicate outputs
        
    def trace_callback(self, outputs, inputs, state, callback_fn=None):
        """Capture callback registration with full context."""
        # Get caller context
        stack = inspect.stack()
        caller_frame = stack[2] if len(stack) > 2 else stack[0]
        
        # Extract output IDs
        output_ids = []
        if isinstance(outputs, (list, tuple)):
            output_ids = [str(o) for o in outputs]
        else:
            output_ids = [str(outputs)]
        
        # Build registration entry
        entry = {
            'timestamp': datetime.now().isoformat(),
            'outputs': output_ids,
            'inputs': [str(i) for i in (inputs if isinstance(inputs, (list, tuple)) else [inputs])],
            'state': [str(s) for s in (state if isinstance(state, (list, tuple)) else [state])] if state else [],
            'caller': {
                'filename': caller_frame.filename,
                'lineno': caller_frame.lineno,
                'function': caller_frame.function,
                'code_context': caller_frame.code_context[0].strip() if caller_frame.code_context else None
            },
            'callback_fn': callback_fn.__name__ if callback_fn and hasattr(callback_fn, '__name__') else str(callback_fn),
            'stack_trace': [
                {
                    'filename': f.filename,
                    'lineno': f.lineno,
                    'function': f.function
                }
                for f in stack[1:10]  # First 10 frames
            ]
        }
        
        # Check for duplicates
        for output_id in output_ids:
            if output_id in self.seen_outputs:
                entry['is_duplicate'] = True
                entry['duplicate_of'] = self.seen_outputs[output_id]
            else:
                self.seen_outputs[output_id] = {
                    'filename': caller_frame.filename,
                    'lineno': caller_frame.lineno,
                    'function': caller_frame.function
                }
        
        self.registrations.append(entry)
        
        # Immediate flush to file (append mode)
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        return entry
    
    def get_duplicate_summary(self):
        """Summarize all duplicate registrations."""
        duplicates = [r for r in self.registrations if r.get('is_duplicate')]
        
        summary = {
            'total_registrations': len(self.registrations),
            'unique_registrations': len(self.registrations) - len(duplicates),
            'duplicate_registrations': len(duplicates),
            'duplicates_by_output': {},
            'duplicates_by_module': {}
        }
        
        # Group by output ID
        for dup in duplicates:
            for output_id in dup['outputs']:
                if output_id not in summary['duplicates_by_output']:
                    summary['duplicates_by_output'][output_id] = []
                summary['duplicates_by_output'][output_id].append({
                    'filename': dup['caller']['filename'],
                    'lineno': dup['caller']['lineno'],
                    'function': dup['caller']['function']
                })
        
        # Group by module
        for dup in duplicates:
            module = Path(dup['caller']['filename']).stem
            if module not in summary['duplicates_by_module']:
                summary['duplicates_by_module'][module] = 0
            summary['duplicates_by_module'][module] += 1
        
        return summary


# Global tracer instance
_tracer = CallbackRegistrationTracer()


def instrument_dash_app(app):
    """
    Instrument a Dash app to trace all callback registrations.
    
    This wraps app.callback() and app.clientside_callback() to log
    registration details.
    """
    # Store original methods
    _original_callback = app.callback
    _original_clientside = getattr(app, 'clientside_callback', None)
    
    def traced_callback(*args, **kwargs):
        """Wrapped callback decorator."""
        # Extract outputs, inputs, state from args/kwargs
        outputs = args[0] if args else kwargs.get('output')
        inputs = args[1] if len(args) > 1 else kwargs.get('inputs', [])
        state = args[2] if len(args) > 2 else kwargs.get('state', [])
        
        # Trace the registration
        _tracer.trace_callback(outputs, inputs, state)
        
        # Call original callback
        return _original_callback(*args, **kwargs)
    
    def traced_clientside(*args, **kwargs):
        """Wrapped clientside callback."""
        if _original_clientside is None:
            return
        
        # Extract outputs, inputs, state
        outputs = kwargs.get('output', args[1] if len(args) > 1 else None)
        inputs = kwargs.get('inputs', args[2] if len(args) > 2 else [])
        state = kwargs.get('state', args[3] if len(args) > 3 else [])
        
        # Trace the registration
        _tracer.trace_callback(outputs, inputs, state, callback_fn='clientside')
        
        # Call original clientside_callback
        return _original_clientside(*args, **kwargs)
    
    # Replace methods
    app.callback = traced_callback
    if _original_clientside:
        app.clientside_callback = traced_clientside
    
    # Store tracer on app for later access
    app._callback_tracer = _tracer
    
    return app


def get_tracer():
    """Get global tracer instance."""
    return _tracer
