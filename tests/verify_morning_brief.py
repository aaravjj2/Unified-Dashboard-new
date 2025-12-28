import sys
import os
import json
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_morning_brief():
    print("🚀 Starting AI Morning Brief Verification...")
    
    try:
        from financial_dashboard.services.ai_morning_brief import AIMorningBriefService
        
        service = AIMorningBriefService()
        print("✅ Service initialized")
        
        print("📊 Generating brief...")
        brief = service.generate_full_brief(watchlist=['AAPL', 'NVDA', 'TSLA'])
        
        # Verify structure
        assert "sections" in brief
        assert len(brief["sections"]) > 0
        
        # Verify specific sections
        summary = next((s for s in brief["sections"] if s["category"] == "summary"), None)
        assert summary is not None
        print("✅ Executive Summary generated")
        
        content = summary["content"]
        print(f"📝 AI Narrative Preview: {content.get('ai_narrative', '')[:100]}...")
        
        if "Market data is available, but AI" in content.get('ai_narrative', ''):
            print("⚠️ LLM generation failed (expected if no local LLM running)")
        else:
            print("✅ LLM generation successful")
            
        # Verify news integration
        events = content.get("key_events", [])
        print(f"📰 Found {len(events)} news events")
        for e in events:
            print(f"  - {e['time']}: {e['event']} ({e['impact']})")
            
        # Verify Portfolio Context
        portfolio = content.get("portfolio_context", {})
        if portfolio:
            print(f"💼 Portfolio Context Found: Equity=${portfolio.get('equity', 0):,.2f}")
            print(f"   Top Holdings: {', '.join(portfolio.get('top_holdings', []))}")
        else:
            print("⚠️ No Portfolio Context (Alpaca keys might be missing)")
            
        # Verify Technicals
        sentiment = content.get("market_sentiment", {})
        factors = sentiment.get("factors", [])
        print(f"📈 Technical Factors: {factors}")
        
        has_advanced_tech = any("RSI" in f or "MACD" in f for f in factors)
        if has_advanced_tech:
            print("✅ Advanced Technicals (RSI/MACD) detected")
        else:
            print("⚠️ No Advanced Technicals detected (SPY history might be unavailable)")

        print("\n✅ Verification Complete: Brief generated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Verification Failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    verify_morning_brief()
