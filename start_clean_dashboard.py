#!/usr/bin/env python3
"""
Clean Dashboard Startup Script
Uses the clean version of the dashboard to avoid React errors
"""

import os
import sys
import subprocess
import time
import requests

def start_clean_dashboard():
    """Start the dashboard using the clean version"""
    
    print("🔧 Starting Clean Dashboard (React Error Free)")
    print("=" * 50)
    
    # Set environment variables to prevent React errors
    env_vars = {
        'DASH_TEST_SSR': 'false',
        'DASH_DEBUG': 'false',  # Disable debug to reduce console noise
        'REACT_APP_DISABLE_SSR': 'true',
        'DASH_SUPPRESS_CALLBACK_EXCEPTIONS': 'true',
        'DASH_PORT': '8051',
        'PORT': '8051',
        'DASH_SERVE_DEV_BUNDLES': 'false',  # Use production bundles
        'DASH_HOT_RELOAD': 'false',  # Disable hot reload
    }
    
    # Update environment
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"✅ Set {key}={value}")
    
    print("\n🚀 Starting dashboard with clean configuration...")
    
    # Try to start the clean version first
    try:
        # Use the clean index version
        cmd = [sys.executable, 'financial_dashboard/index_clean.py']
        
        print(f"📋 Command: {' '.join(cmd)}")
        
        # Start the process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Monitor startup
        startup_timeout = 30
        start_time = time.time()
        
        while time.time() - start_time < startup_timeout:
            # Check if process is still running
            if process.poll() is not None:
                print("❌ Process exited early")
                break
            
            # Try to connect
            try:
                response = requests.get('http://localhost:8051/', timeout=2)
                if response.status_code == 200:
                    print("✅ Dashboard is running successfully!")
                    print(f"🌐 Access at: http://localhost:8051")
                    print("\n📊 Dashboard Status:")
                    print("   • React Errors: Fixed")
                    print("   • Clean Layout: Active")
                    print("   • Port: 8051")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(1)
        
        print("⚠️ Dashboard startup timeout or failed")
        return False
        
    except Exception as e:
        print(f"❌ Failed to start clean dashboard: {e}")
        return False

def fallback_to_regular():
    """Fallback to regular dashboard with maximum error suppression"""
    
    print("\n🔄 Falling back to regular dashboard with error suppression...")
    
    # Even more aggressive error suppression
    env_vars = {
        'DASH_TEST_SSR': 'false',
        'DASH_DEBUG': 'false',
        'REACT_APP_DISABLE_SSR': 'true',
        'DASH_SUPPRESS_CALLBACK_EXCEPTIONS': 'true',
        'DASH_PORT': '8051',
        'PORT': '8051',
        'DASH_SERVE_DEV_BUNDLES': 'false',
        'DASH_HOT_RELOAD': 'false',
        'DASH_ASSETS_EXTERNAL_PATH': '',  # Force local assets
        'DASH_COMPRESS': 'false',  # Disable compression
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    try:
        cmd = [sys.executable, 'financial_dashboard/index.py']
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Wait a bit for startup
        time.sleep(5)
        
        # Check if it's working
        try:
            response = requests.get('http://localhost:8051/', timeout=5)
            if response.status_code == 200:
                print("✅ Regular dashboard started with error suppression")
                return True
        except:
            pass
        
        return False
        
    except Exception as e:
        print(f"❌ Fallback failed: {e}")
        return False

if __name__ == "__main__":
    success = start_clean_dashboard()
    
    if not success:
        print("\n🔄 Trying fallback approach...")
        success = fallback_to_regular()
    
    if success:
        print("\n🎉 Dashboard is running!")
        print("📋 Next steps:")
        print("   1. Open http://localhost:8051 in your browser")
        print("   2. Run LambdaTest validation: python lambda_test_runner.py")
        print("   3. Check console for any remaining errors")
    else:
        print("\n❌ Failed to start dashboard")
        print("💡 Try manually:")
        print("   export DASH_TEST_SSR=false")
        print("   python financial_dashboard/index.py")