"""
Test action extraction by directly calling generator with action-focused prompt
"""
import sys
sys.path.insert(0, '/home/aarav/unified-dashboard')

from financial_dashboard.services.chat.generator_client import get_generator

gen = get_generator()

# Test direct prompt
action_prompt = "User wants to create a paper trade order to buy 10 AAPL at market price"

print("Testing deterministic action generation...")
response = gen.complete(action_prompt, max_tokens=256)

print(f"\nResponse text:\n{response.text}")
print(f"\nModel: {response.model}")
print(f"Tokens: {response.total_tokens}")

# Try to parse as JSON
import json
try:
    if '{' in response.text:
        start = response.text.index('{')
        end = response.text.rindex('}') + 1
        json_str = response.text[start:end]
        action = json.loads(json_str)
        print(f"\n✅ Successfully extracted action:")
        print(json.dumps(action, indent=2))
    else:
        print("\n❌ No JSON found in response")
except Exception as e:
    print(f"\n❌ Failed to parse action: {e}")
