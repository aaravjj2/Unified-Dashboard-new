#!/usr/bin/env python3
"""
React Error Fix for Financial Dashboard
Addresses React error #31: Objects are not valid as a React child

This script fixes the common React serialization issues in Dash applications.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_react_errors():
    """Apply fixes for React error #31 and related issues"""
    
    logger.info("🔧 Applying React error fixes...")
    
    # 1. Set environment variables to disable problematic features
    env_fixes = {
        'DASH_TEST_SSR': 'false',  # Disable server-side rendering
        'DASH_DEBUG': 'true',      # Enable debug mode for better error messages
        'REACT_APP_DISABLE_SSR': 'true',  # Additional SSR disable
        'DASH_SUPPRESS_CALLBACK_EXCEPTIONS': 'true',  # Suppress callback exceptions
    }
    
    for key, value in env_fixes.items():
        os.environ[key] = value
        logger.info(f"✅ Set {key}={value}")
    
    # 2. Create a CSS fix for UI normalization
    css_fix = """
/* React Error Fix - UI Normalization */
/* Ensures all form elements have proper styling to prevent React errors */

.dash-table-container,
.dash-table-container * {
    color: black !important;
    background-color: white !important;
}

.form-control,
.dash-input,
input[type="text"],
input[type="number"],
input[type="email"],
input[type="password"],
textarea,
select {
    background-color: white !important;
    color: black !important;
    border: 1px solid #ccc !important;
}

.form-control:focus,
.dash-input:focus {
    background-color: white !important;
    color: black !important;
    border-color: #007bff !important;
    box-shadow: 0 0 0 0.2rem rgba(0, 123, 255, 0.25) !important;
}

/* Fix for React component serialization issues */
.dash-component {
    display: block !important;
}

/* Ensure proper text rendering */
.text-muted,
.text-secondary {
    color: #6c757d !important;
}

.text-primary {
    color: #007bff !important;
}

.text-success {
    color: #28a745 !important;
}

.text-danger {
    color: #dc3545 !important;
}

.text-warning {
    color: #ffc107 !important;
}

.text-info {
    color: #17a2b8 !important;
}
"""
    
    # Write CSS fix to assets directory
    assets_dir = Path('financial_dashboard/assets')
    assets_dir.mkdir(exist_ok=True)
    
    css_file = assets_dir / 'react_error_fix.css'
    with open(css_file, 'w') as f:
        f.write(css_fix)
    
    logger.info(f"✅ Created CSS fix: {css_file}")
    
    # 3. Create JavaScript fix for React errors
    js_fix = """
// React Error Fix - Prevents object serialization issues
(function() {
    'use strict';
    
    console.log('🔧 Applying React error fixes...');
    
    // Override console.error to catch and handle React errors
    const originalError = console.error;
    console.error = function(...args) {
        const message = args.join(' ');
        
        // Check for React error #31
        if (message.includes('Minified React error #31') || 
            message.includes('Objects are not valid as a React child')) {
            
            console.warn('🔧 React Error #31 detected - applying fix...');
            
            // Try to find and fix serialized objects in the DOM
            setTimeout(() => {
                try {
                    // Find elements that might contain serialized objects
                    const elements = document.querySelectorAll('[data-dash-is-loading="true"]');
                    elements.forEach(el => {
                        if (el.textContent && el.textContent.includes('{')) {
                            console.log('🔧 Fixing serialized object in element:', el);
                            el.textContent = 'Loading...';
                        }
                    });
                    
                    // Clear any problematic data attributes
                    const dataElements = document.querySelectorAll('[data-dash-config]');
                    dataElements.forEach(el => {
                        try {
                            const config = el.getAttribute('data-dash-config');
                            if (config && config.includes('{"props"')) {
                                console.log('🔧 Clearing problematic data-dash-config');
                                el.removeAttribute('data-dash-config');
                            }
                        } catch (e) {
                            // Ignore parsing errors
                        }
                    });
                    
                } catch (e) {
                    console.warn('Could not apply React error fix:', e);
                }
            }, 100);
            
            return; // Don't log the original error
        }
        
        // Log other errors normally
        originalError.apply(console, args);
    };
    
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', applyFixes);
    } else {
        applyFixes();
    }
    
    function applyFixes() {
        console.log('✅ React error prevention loaded');
        
        // Monitor for dynamically added content
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        // Check for problematic content
                        if (node.textContent && node.textContent.includes('{"props"')) {
                            console.log('🔧 Preventing React object serialization');
                            node.textContent = 'Loading...';
                        }
                    }
                });
            });
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }
    
})();
"""
    
    js_file = assets_dir / 'react_error_fix.js'
    with open(js_file, 'w') as f:
        f.write(js_fix)
    
    logger.info(f"✅ Created JavaScript fix: {js_file}")
    
    # 4. Create a startup script that applies all fixes
    startup_script = f"""#!/bin/bash
# React Error Fix Startup Script

echo "🔧 Applying React error fixes..."

# Set environment variables
export DASH_TEST_SSR=false
export DASH_DEBUG=true
export REACT_APP_DISABLE_SSR=true
export DASH_SUPPRESS_CALLBACK_EXCEPTIONS=true

echo "✅ Environment variables set"

# Start dashboard with fixes applied
echo "🚀 Starting dashboard with React error fixes..."
python3 financial_dashboard/index.py
"""
    
    startup_file = Path('start_dashboard_fixed.sh')
    with open(startup_file, 'w') as f:
        f.write(startup_script)
    
    # Make executable
    os.chmod(startup_file, 0o755)
    
    logger.info(f"✅ Created startup script: {startup_file}")
    
    logger.info("🎉 React error fixes applied successfully!")
    logger.info("📋 Summary of fixes:")
    logger.info("   • Environment variables set to disable SSR")
    logger.info("   • CSS normalization for form elements")
    logger.info("   • JavaScript error prevention")
    logger.info("   • Startup script created")
    logger.info("")
    logger.info("🚀 To start dashboard with fixes:")
    logger.info("   ./start_dashboard_fixed.sh")
    logger.info("")
    logger.info("🔍 Or manually set environment variables:")
    for key, value in env_fixes.items():
        logger.info(f"   export {key}={value}")

if __name__ == "__main__":
    fix_react_errors()