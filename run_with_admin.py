#!/usr/bin/env python3
"""Local helper to run the dashboard with admin diagnostics registered.

This file is intentionally local-only (dev helper). It imports the project's
app factory, creates the app, registers the `admin_bp` blueprint from
`api.admin_diagnostics`, and starts the server on PORT (default 8029).

Do NOT commit this into production startup paths. It's for local testing only.
"""
import os
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('run_with_admin')


def main():
    port = int(os.getenv('PORT', '8029'))
    host = os.getenv('HOST', '127.0.0.1')
    debug = os.getenv('DEBUG', 'False').lower() in ('1', 'true', 'yes')

    logger.info('Initializing application via financial_dashboard.index.initialize_app...')
    try:
        from financial_dashboard.index import initialize_app
    except Exception as e:
        logger.error('Failed to import initialize_app from financial_dashboard.index: %s', e)
        sys.exit(1)

    try:
        app = initialize_app()
    except Exception as e:
        logger.error('initialize_app() failed: %s', e)
        sys.exit(1)

    # Determine the Flask server object to register blueprints on.
    server = getattr(app, 'server', None) or app

    try:
        from api.admin_diagnostics import admin_bp
    except Exception as e:
        logger.error('Failed to import admin_diagnostics.admin_bp: %s', e)
        sys.exit(1)

    # Register blueprint without extra url_prefix to avoid double '/admin/admin'.
    try:
        server.register_blueprint(admin_bp)
        logger.info('Registered admin diagnostics blueprint')
    except Exception as e:
        logger.error('Failed to register admin blueprint: %s', e)

    logger.info('Starting server on %s:%s (debug=%s)', host, port, debug)
    try:
        # app may be a Flask app or Dash app with .run method
        if hasattr(app, 'run'):
            app.run(host=host, port=port, debug=debug)
        else:
            # Fallback: try running underlying Flask server if available
            server.run(host=host, port=port, debug=debug)
    except Exception as e:
        logger.error('Server failed to start: %s', e)
        sys.exit(1)


if __name__ == '__main__':
    main()
