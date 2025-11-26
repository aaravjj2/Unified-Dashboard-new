import requests
import json
import time

BASE_URL = "http://localhost:8062/api/chat"

questions = [
    "What is the current price of SPY?",
    "What are my current portfolio positions?",
    "Explain implied volatility.",
    "What is an Iron Condor strategy?",
    "How does Theta affect option prices?",
    "What is the difference between a call and a put?",
    "Analyze the market trend for AAPL.",
    "What is the VIX index?",
    "How do I hedge my portfolio?",
    "What is the price of NVDA?",
    "Tell me about the current volatility surface for SPY."
]

def test_chatbot():
    print("=== Testing Mistral-7B-Instruct Chatbot ===")
    print(f"Target URL: {BASE_URL}")
    print("-" * 50)
    
    for i, q in enumerate(questions, 1):
        print(f"\n[Question {i}]: {q}")
        start_time = time.time()
        try:
            response = requests.post(BASE_URL, json={"message": q}, timeout=60)
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                print(f"[Response ({elapsed:.2f}s)]:")
                print(data.get('response', 'No response text'))
                if data.get('sources'):
                    print(f"[Sources]: {data.get('sources')}")
            else:
                print(f"[Error]: Status {response.status_code}")
                print(response.text)
        except Exception as e:
            print(f"[Exception]: {e}")
            
        print("-" * 50)
        time.sleep(2)

if __name__ == "__main__":
    test_chatbot()
