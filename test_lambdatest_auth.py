#!/usr/bin/env python3
"""
Test LambdaTest Authentication
"""

import requests
import os

def test_lambdatest_auth():
    username = "aaravj"
    access_key = "LT_520EQUeJP1lj3nQvgtQtKM1Vobz9I4zog0KN9yEPwAczBNe"
    
    print(f"Testing LambdaTest authentication...")
    print(f"Username: {username}")
    print(f"Access Key: {access_key[:10]}...")
    
    # Test different endpoints
    endpoints = [
        "https://api.lambdatest.com/automation/api/v1/platforms",
        "https://api.lambdatest.com/screenshots/v1/sessions",
        "https://accounts.lambdatest.com/api/user/token"
    ]
    
    for endpoint in endpoints:
        try:
            print(f"\n🔍 Testing endpoint: {endpoint}")
            
            auth = (username, access_key)
            response = requests.get(endpoint, auth=auth, timeout=10)
            
            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                print("✅ Authentication successful!")
                try:
                    data = response.json()
                    print(f"Response data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                except:
                    print("Response is not JSON")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                print(f"Response text: {response.text[:200]}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    return False

if __name__ == "__main__":
    success = test_lambdatest_auth()
    if not success:
        print("\n💡 Suggestions:")
        print("1. Check if credentials are correct")
        print("2. Verify account is active")
        print("3. Check if API access is enabled")
        print("4. Try logging into LambdaTest web interface")