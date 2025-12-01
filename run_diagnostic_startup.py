#!/usr/bin/env python3
"""
Diagnostic startup script for Research Lab visibility issue.

This script:
1. Enables verbose logging
2. Captures startup sequence
3. Validates tab registration
4. Generates diagnostic report
"""

import os
import sys
import logging
from datetime import datetime

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('diagnostics_research_lab.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Run diagnostic startup."""
    logger.info("=" * 80)
    logger.info("RESEARCH LAB DIAGNOSTIC STARTUP")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("=" * 80)
    
    # Change to project directory
    project_dir = '/mnt/c/Aarav/fin_env/unified-dashboard'
    os.chdir(project_dir)
    sys.path.insert(0, os.path.join(project_dir, 'financial_dashboard'))
    
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Python path: {sys.path[:3]}")
    
    try:
        # Import and run the dashboard
        logger.info("\n📦 Importing financial_dashboard.index...")
        from financial_dashboard.index import create_app
        
        logger.info("\n🔨 Creating app instance...")
        app = create_app()
        
        logger.info("\n✅ App created successfully!")
        logger.info(f"App type: {type(app)}")
        logger.info(f"Server type: {type(app.server)}")
        
        # Check callback registration
        if hasattr(app, 'callback_map'):
            logger.info(f"\n📊 Callback map contains {len(app.callback_map)} callbacks")
            
            # Find research lab callbacks
            research_callbacks = [
                cb for cb in app.callback_map.keys() 
                if 'research' in str(cb).lower()
            ]
            logger.info(f"🔬 Research Lab callbacks: {len(research_callbacks)}")
            for cb in research_callbacks[:5]:
                logger.info(f"  - {cb}")
        
        # Start server
        logger.info("\n🚀 Starting server on port 8050...")
        logger.info("Dashboard should be accessible at http://localhost:8050")
        logger.info("\nPress Ctrl+C to stop the server\n")
        
        app.run(host='0.0.0.0', port=8050, debug=True)
        
    except ImportError as e:
        logger.error(f"\n❌ Import error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == '__main__':
    main()
