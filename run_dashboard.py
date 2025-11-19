#!/usr/bin/env python3
"""
Dashboard Runner - Entry Point for Financial Dashboard
Starts the dashboard server on port 8090.

Usage:
    python run_dashboard.py
    
Environment Variables:
    PORT: Override default port (default: 8090)
    HOST: Override default host (default: 0.0.0.0)
    DEBUG: Enable debug mode (default: False)
"""
import os
import sys
import logging
import socket

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_port_available(host: str, port: int) -> bool:
    """
    Check if a port is available for binding.
    
    Args:
        host: Host address to check
        port: Port number to check
        
    Returns:
        True if port is available, False otherwise
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
        sock.close()
        return True
    except OSError:
        return False


def main():
    """Run the dashboard server on port 8090."""
    # Get configuration from environment
    port = int(os.getenv('PORT', 8090))
    host = os.getenv('HOST', '0.0.0.0')
    debug = os.getenv('DEBUG', 'False').lower() in ('true', '1', 'yes')
    
    logger.info("=" * 60)
    logger.info("Financial Dashboard - Starting")
    logger.info("=" * 60)
    logger.info(f"Host: {host}")
    logger.info(f"Port: {port}")
    logger.info(f"Debug: {debug}")
    logger.info("=" * 60)
    
    # Check if port is available
    if not check_port_available(host, port):
        logger.error("")
        logger.error("=" * 60)
        logger.error(f"ERROR: Port {port} is already in use!")
        logger.error("=" * 60)
        logger.error("")
        logger.error("Resolution steps:")
        logger.error(f"  1. Find the process using the port:")
        logger.error(f"     lsof -i :{port}")
        logger.error(f"     # or on Linux:")
        logger.error(f"     netstat -tulpn | grep :{port}")
        logger.error("")
        logger.error(f"  2. Kill the process:")
        logger.error(f"     kill -9 <PID>")
        logger.error("")
        logger.error(f"  3. Or use a different port:")
        logger.error(f"     PORT=8091 python run_dashboard.py")
        logger.error("")
        logger.error("=" * 60)
        sys.exit(1)
    
    # Import and create app
    try:
        logger.info("Importing dashboard application...")
        from financial_dashboard.app import create_app
        
        logger.info("Creating application instance...")
        app = create_app()
        
        logger.info("Application created successfully!")
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"Dashboard is starting on http://{host}:{port}")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Press CTRL+C to stop the server")
        logger.info("")
        
        # Start server
        app.run(
            host=host,
            port=port,
            debug=debug
        )
        
    except ImportError as e:
        logger.error("")
        logger.error("=" * 60)
        logger.error("ERROR: Failed to import dashboard application")
        logger.error("=" * 60)
        logger.error(f"Error: {e}")
        logger.error("")
        logger.error("Make sure you're in the correct directory and dependencies are installed:")
        logger.error("  pip install -r requirements.txt")
        logger.error("")
        logger.error("=" * 60)
        sys.exit(1)
        
    except Exception as e:
        logger.error("")
        logger.error("=" * 60)
        logger.error("ERROR: Failed to start dashboard")
        logger.error("=" * 60)
        logger.error(f"Error: {e}")
        logger.error("")
        import traceback
        logger.error(traceback.format_exc())
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == '__main__':
    main()
