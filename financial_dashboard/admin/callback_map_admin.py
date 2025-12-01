"""
Admin endpoint for callback map inspection.
Provides runtime visibility into registered callbacks.
"""
from flask import jsonify
import logging

logger = logging.getLogger(__name__)

def register_callback_admin_endpoint(server, app):
    """
    Register the /admin/callback_map endpoint to inspect callback registrations.
    
    Args:
        server: Flask server instance
        app: Dash app instance
    """
    
    @server.route('/admin/callback_map')
    def admin_callback_map():
        """Return the current callback map for inspection."""
        try:
            callback_map = getattr(app, 'callback_map', {})
            
            # Build output ID to callback mapping
            output_id_to_callbacks = {}
            duplicate_outputs = []
            
            for callback_id, callback_spec in callback_map.items():
                # Extract outputs
                outputs = callback_spec.get('output', [])
                if not isinstance(outputs, list):
                    outputs = [outputs]
                
                for output in outputs:
                    # Get output ID string
                    if hasattr(output, 'component_id') and hasattr(output, 'component_property'):
                        output_id = f"{output.component_id}.{output.component_property}"
                    else:
                        output_id = str(output)
                    
                    if output_id not in output_id_to_callbacks:
                        output_id_to_callbacks[output_id] = []
                    output_id_to_callbacks[output_id].append(callback_id)
            
            # Find duplicates
            for output_id, callback_ids in output_id_to_callbacks.items():
                if len(callback_ids) > 1:
                    duplicate_outputs.append({
                        'output_id': output_id,
                        'count': len(callback_ids),
                        'callback_ids': callback_ids
                    })
            
            return jsonify({
                'status': 'success',
                'total_callbacks': len(callback_map),
                'callback_ids': list(callback_map.keys()),
                'duplicate_outputs': duplicate_outputs,
                'duplicate_count': len(duplicate_outputs),
                'output_id_counts': {k: len(v) for k, v in output_id_to_callbacks.items()},
                'app_id': id(app),
                'app_type': str(type(app))
            })
            
        except Exception as e:
            logger.exception("Error in /admin/callback_map")
            import traceback
            return jsonify({
                'status': 'error',
                'error': str(e),
                'traceback': traceback.format_exc()
            }), 500
