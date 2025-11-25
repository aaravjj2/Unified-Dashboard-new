"""
Test script to verify action suggestion extraction from RAG responses
"""
import sys
sys.path.insert(0, '/home/aarav/unified-dashboard')

from financial_dashboard.services.chat.rag import get_rag

# Test case 1: Explicit action request
test_queries = [
    "What is the top weekly pick?",  # Should NOT suggest action
    "Create a paper order to buy 10 AAPL at market price"  # SHOULD suggest action
]

rag = get_rag()

for query in test_queries:
    print(f"\n{'='*80}")
    print(f"QUERY: {query}")
    print('='*80)
    
    result = rag.answer_query(query, use_rag=True, top_k=5)
    
    print(f"\nAnswer: {result['answer'][:300]}...")
    print(f"Action Suggestion: {result.get('action_suggestion')}")
    print(f"Retrieved {len(result['sources'])} sources")
    
    if result.get('action_suggestion'):
        print(f"\nExtracted Action:")
        import json
        print(json.dumps(result['action_suggestion'], indent=2))
