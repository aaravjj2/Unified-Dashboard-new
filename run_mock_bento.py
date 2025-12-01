#!/usr/bin/env python3
"""Local helper to run the mock Bento service on a configurable port.

This is a dev helper (local-only). It imports the Flask `app` from
`services.mock_bento.app` and runs it on the port defined by the
`PORT` environment variable (default 5001).
"""
import os
import logging
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('run_mock_bento')


def main():
    port = int(os.getenv('PORT', '5001'))
    host = os.getenv('HOST', '0.0.0.0')
    debug = os.getenv('DEBUG', 'False').lower() in ('1', 'true', 'yes')

    logger.info('Starting mock Bento on %s:%s (debug=%s)', host, port, debug)
    try:
        from services.mock_bento.app import app
    except Exception as e:
        logger.error('Failed to import mock Bento app: %s', e)
        sys.exit(1)

    try:
        app.run(host=host, port=port, debug=debug)
    except Exception as e:
        logger.error('Failed to run mock Bento: %s', e)
        sys.exit(1)


if __name__ == '__main__':
    main()
