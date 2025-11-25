#!/usr/bin/env python3
"""
GPU-Accelerated Chat Performance Test
Tests chatbot response time with GPU acceleration
"""

import time
import requests
import json
import sys

def test_chat_performance():
    """Send test message and measure response time"""
    
    url = "http://localhost:8050/_dash-update-component"
    
    # Test message payload
    payload = {
        "output": "chat-window.data..chat-messages.children..chat-output.children..chat-history.data",
        "outputs": {
            "id": "chat-window",
            "property": "data"
        },
        "inputs": [
            {
                "id": "chat-send-btn",
                "property": "n_clicks",
                "value": 1
            },
            {
                "id": "chat-input",
                "property": "value", 
                "value": "What is portfolio optimization?"
            },
            {
                "id": "chat-history",
                "property": "data",
                "value": []
            }
        ],
        "changedPropIds": ["chat-send-btn.n_clicks"],
        "state": []
    }
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    
    print("=" * 60)
    print("GPU-ACCELERATED CHAT PERFORMANCE TEST")
    print("=" * 60)
    print(f"\nTest Query: 'What is portfolio optimization?'")
    print(f"Expected GPU time: <5 seconds")
    print(f"Previous CPU time: 30-60 seconds")
    print("\nSending request...")
    
    start_time = time.time()
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=120)
        end_time = time.time()
        
        elapsed = end_time - start_time
        
        print(f"\n✓ Response received in {elapsed:.2f} seconds")
        
        if response.status_code == 200:
            data = response.json()
            
            # Extract response text
            if "response" in data:
                resp_data = data["response"]
                if isinstance(resp_data, dict) and "props" in resp_data:
                    children = resp_data["props"].get("children", [])
                    if children and len(children) > 0:
                        last_msg = children[-1]
                        if isinstance(last_msg, dict) and "props" in last_msg:
                            text = last_msg["props"].get("children", "")
                            print(f"\nAI Response Preview:")
                            print(f"{text[:200]}...")
            
            # Performance evaluation
            print(f"\n{'='*60}")
            print(f"PERFORMANCE SUMMARY")
            print(f"{'='*60}")
            print(f"Response Time: {elapsed:.2f}s")
            
            if elapsed < 5:
                print(f"✅ EXCELLENT - GPU acceleration working optimally")
                print(f"✅ {((60-elapsed)/60*100):.0f}% faster than CPU baseline")
            elif elapsed < 15:
                print(f"✅ GOOD - GPU acceleration active")
                print(f"⚠️  Some GPU optimization possible")
            elif elapsed < 30:
                print(f"⚠️  MODERATE - Partial GPU usage or overhead")
            else:
                print(f"❌ SLOW - Likely still using CPU")
                print(f"❌ Check logs for GPU initialization errors")
            
            print(f"{'='*60}")
            return elapsed < 15  # Success if under 15s
            
        else:
            print(f"\n❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
            
    except requests.Timeout:
        print(f"\n❌ Request timed out after 120 seconds")
        print(f"❌ GPU acceleration likely failed, fell back to slow CPU")
        return False
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_chat_performance()
    sys.exit(0 if success else 1)
