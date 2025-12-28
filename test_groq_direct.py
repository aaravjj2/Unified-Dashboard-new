#!/usr/bin/env python3
"""Test GROQ API directly"""

import os
from financial_dashboard.utils.load_keys_env import load_keys_env

# Load keys
load_keys_env()

groq_key = os.getenv('GROQ_API_KEY')
print(f"GROQ_API_KEY loaded: {groq_key[:20]}..." if groq_key else "GROQ_API_KEY: NOT FOUND")

# Test API call
import requests

headers = {
    'Authorization': f'Bearer {groq_key}',
    'Content-Type': 'application/json'
}

data = {
    'model': 'llama-3.3-70b-versatile',  # Updated model
    'messages': [
        {'role': 'system', 'content': 'You are a financial analyst.'},
        {'role': 'user', 'content': 'What is 2+2?'}
    ],
    'temperature': 0.7,
    'max_tokens': 50
}

try:
    response = requests.post('https://api.groq.com/openai/v1/chat/completions', 
                           headers=headers, json=data, timeout=10)
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ GROQ API working!")
        print(f"Response: {result['choices'][0]['message']['content']}")
    else:
        print(f"\n❌ GROQ API error: {response.status_code}")
        print(f"Response: {response.text}")
except Exception as e:
    print(f"\n❌ GROQ API exception: {e}")
