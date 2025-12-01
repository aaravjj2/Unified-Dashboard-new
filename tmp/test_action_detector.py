"""
Enhanced RAG with pattern-based action detection
Adds intent detection layer before calling generator
"""
import re
from typing import Optional, Dict, Any


class ActionIntentDetector:
    """
    Pre-LLM action intent detection using pattern matching
    Reduces reliance on small LLM for action extraction
    """
    
    PATTERNS = {
        "create_paper_order": [
            r"(?:create|place|submit|buy|sell).{0,30}(?:order|trade|position)",
            r"(?:buy|sell)\s+\d+\s+(?:shares?\s+of\s+)?[A-Z]{1,5}",
            r"paper\s+(?:order|trade)",
        ],
        "open_tab": [
            r"(?:open|show|navigate to|go to).{0,20}(?:tab|page|view)",
            r"show\s+me.{0,20}(?:volatility|trends|news|positions)",
        ],
        "run_backtest": [
            r"(?:run|execute|start).{0,20}backtest",
            r"test.{0,20}strategy",
        ]
    }
    
    def detect(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Detect action intent from query
        
        Returns:
            Action suggestion dict or None
        """
        query_lower = query.lower()
        
        for action_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return self._build_action(action_type, query)
        
        return None
    
    def _build_action(self, action_type: str, query: str) -> Optional[Dict[str, Any]]:
        """Build action suggestion from detected intent"""
        
        if action_type == "create_paper_order":
            # Extract ticker and quantity
            ticker_match = re.search(r'\b([A-Z]{1,5})\b', query)
            qty_match = re.search(r'\b(\d+)\s+(?:shares?)?', query)
            side_match = re.search(r'\b(buy|sell)\b', query.lower())
            
            ticker = ticker_match.group(1) if ticker_match else "AAPL"
            qty = int(qty_match.group(1)) if qty_match else 1
            side = side_match.group(1) if side_match else "buy"
            
            payload = {
                "symbol": ticker,
                "qty": qty,
                "side": side,
                "type": "market",
                "paper": True
            }
            return {
                "action": "create_paper_order",
                "payload": payload,
                "confidence": 0.85,
                "method": "pattern_detection"
            }
        
        elif action_type == "open_tab":
            # Extract tab name
            tab_keywords = {
                "volatility": "vol-surface",
                "vol": "vol-surface",
                "trends": "market-trends",
                "news": "market-trends",
                "positions": "positions",
                "portfolio": "positions"
            }
            
            tab_name = "market-trends"  # default
            for keyword, tab in tab_keywords.items():
                if keyword in query.lower():
                    tab_name = tab
                    break
            
            return {
                "action": "open_tab",
                "payload": {
                    "tab_name": tab_name
                },
                "confidence": 0.75,
                "method": "pattern_detection"
            }
        
        return None


# Test
if __name__ == "__main__":
    detector = ActionIntentDetector()
    
    test_queries = [
        "Create a paper order to buy 10 shares of AAPL",
        "Buy 5 TSLA at market",
        "Show me the volatility tab",
        "What are the top picks?",  # Should NOT detect action
        "Run a backtest on momentum strategy"
    ]
    
    for query in test_queries:
        result = detector.detect(query)
        print(f"\nQuery: {query}")
        print(f"Action: {result}")
