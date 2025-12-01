#!/usr/bin/env python3
"""Test no-chunk guard in RAG orchestrator"""
import requests
import json
import sys

DASHBOARD_URL = "http://localhost:8050"

def test_no_chunk_guard():
    """Test query for completely irrelevant topic that should trigger guard"""
    queries = [
        "What is the recipe for chocolate chip cookies?",
        "How do I train a neural network?",
        "What is the capital of France?"
    ]
    
    print("=" * 80)
    print("Testing No-Chunk Guard")
    print("=" * 80)
    
    for query in queries:
        print(f"\n📤 Query: {query}")
        
        response = requests.post(
            f"{DASHBOARD_URL}/api/chat/query",
            json={
                "query": query,
                "use_rag": True,
                "top_k": 3
            },
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            print(f"❌ HTTP {response.status_code}: {response.text}")
            continue
        
        data = response.json()
        
        print(f"✅ Response received")
        print(f"   Answer: {data.get('answer', '')[:150]}...")
        print(f"   Sources: {len(data.get('sources', []))}")
        print(f"   Retrievals: {len(data.get('retrievals', []))}")
        
        if data.get('retrievals'):
            print(f"   Top chunk scores: {[r['score'] for r in data['retrievals'][:3]]}")
        
        metadata = data.get('metadata', {})
        if metadata.get('no_chunks_found'):
            print(f"   ✅ NO-CHUNK GUARD TRIGGERED")
        
        action = data.get('action_suggestion')
        if action:
            print(f"   Action suggested: {action.get('action')}")
    
    print("\n" + "=" * 80)
    print("Test complete")
    print("=" * 80)

if __name__ == "__main__":
    test_no_chunk_guard()
