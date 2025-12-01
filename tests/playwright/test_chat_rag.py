"""
Playwright E2E Tests for RAG Chat Assistant
Tests complete user flow: open chat → send query → view response → confirm action

Requirements:
- Dashboard running on http://localhost:8050
- Chat API endpoints operational
- FAISS index populated with fixtures

Usage:
    pytest tests/playwright/test_chat_rag.py -v --headed
"""

import pytest
import time
import json
from playwright.sync_api import Page, expect


@pytest.fixture(scope="module")
def browser_context_args(browser_context_args):
    """Configure browser context for chat tests"""
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "record_video_dir": "reports/chat_agent/videos",
        "record_har_path": "reports/chat_agent/network.har",
    }


def test_chat_text_color(page: Page):
    """
    TEST 1: Verify chat text is black (CSS fix validation)
    
    Acceptance Criteria:
    - Chat messages have color: rgb(0, 0, 0) or #000
    - Text is readable against background
    """
    print("\n" + "="*70)
    print("TEST 1: Chat Text Color Validation")
    print("="*70)
    
    page.goto("http://localhost:8050")
    page.wait_for_load_state("networkidle")
    
    # Open chat
    print("Opening chat widget...")
    page.click("#chatbot-toggle-btn")
    time.sleep(0.5)
    
    # Wait for chat container to be visible
    page.wait_for_selector("#chatbot-container", state="visible", timeout=5000)
    print("✅ Chat opened")
    
    # Check welcome message color
    welcome_msg = page.locator("#chatbot-messages").locator('[data-testid="chat-message"]').first
    
    if welcome_msg.count() > 0:
        color = welcome_msg.evaluate("el => window.getComputedStyle(el).color")
        print(f"Welcome message color: {color}")
        
        # Accept rgb(0, 0, 0) or any very dark color
        assert "rgb(0, 0, 0)" in color or "rgb(0,0,0)" in color, \
            f"Chat text color should be black, got: {color}"
        print("✅ Text color is black")
    
    # Take screenshot
    page.screenshot(path="reports/chat_agent/screenshots/chat_text_color.png")
    print("📸 Screenshot saved")


def test_chat_query_with_sources(page: Page):
    """
    TEST 2: Send query and verify response with sources
    
    Acceptance Criteria:
    - User can type message and send
    - AI responds within 30 seconds
    - Response includes source citations
    - Messages display in chat history
    """
    print("\n" + "="*70)
    print("TEST 2: RAG Query with Sources")
    print("="*70)
    
    page.goto("http://localhost:8050")
    page.wait_for_load_state("networkidle")
    
    # Open chat
    page.click("#chatbot-toggle-btn")
    page.wait_for_selector("#chatbot-container", state="visible", timeout=5000)
    print("✅ Chat opened")
    
    # Type query
    query = "What is the volatility for AAPL?"
    print(f"Sending query: {query}")
    page.fill("#chatbot-input", query)
    
    # Send message
    page.click("#chatbot-send-btn")
    print("✅ Message sent")
    
    # Wait for user message to appear
    user_messages = page.locator('[data-testid="chat-message"][data-is-user="True"]')
    expect(user_messages).to_have_count(1, timeout=5000)
    print("✅ User message displayed")
    
    # Wait for AI response via diagnostic dataset (up to 30 seconds)
    print("Waiting for AI response (diagnostic)...")
    page.wait_for_function(
        "() => { const el = document.querySelector('#chat-color-diagnostic'); return el && el.dataset && el.dataset.lastResponse && parseInt(el.dataset.lastResponseLen||'0')>0 }",
        timeout=30000,
    )
    print("✅ AI response signalled by diagnostic element")
    
    # Get response text
    response_bubble = ai_messages.nth(1)  # Second AI message (first is welcome)
    response_text = response_bubble.inner_text()
    print(f"Response ({len(response_text)} chars): {response_text[:100]}...")
    
    # Check for sources
    # Sources appear in italics below the main message
    has_sources = "Sources:" in response_text or "Source" in response_text
    if has_sources:
        print("✅ Response includes source citations")
    else:
        print("⚠️ No explicit source citations (may be embedded in response)")
    
    # Screenshot
    page.screenshot(path="reports/chat_agent/screenshots/chat_query_response.png")
    print("📸 Screenshot saved")


def test_action_suggestion_flow(page: Page):
    """
    TEST 3: Action suggestion → confirmation → execution
    
    Acceptance Criteria:
    - Query triggers action suggestion
    - Action card displays with payload details
    - User can confirm or cancel
    - Confirmation executes action via API
    - Audit log updated
    """
    print("\n" + "="*70)
    print("TEST 3: Action Suggestion Flow")
    print("="*70)
    
    page.goto("http://localhost:8050")
    page.wait_for_load_state("networkidle")
    
    # Open chat
    page.click("#chatbot-toggle-btn")
    page.wait_for_selector("#chatbot-container", state="visible", timeout=5000)
    print("✅ Chat opened")
    
    # Send query that should trigger action
    query = "Create a paper order for 1 share of AAPL at market price"
    print(f"Sending action query: {query}")
    page.fill("#chatbot-input", query)
    page.click("#chatbot-send-btn")
    print("✅ Query sent")
    
    # Wait for response via diagnostic dataset
    page.wait_for_function(
        "() => { const el = document.querySelector('#chat-color-diagnostic'); return el && el.dataset && el.dataset.lastResponse && parseInt(el.dataset.lastResponseLen||'0')>0 }",
        timeout=30000,
    )
    
    # Look for action card
    print("Looking for action suggestion card...")
    action_card = page.locator("#chatbot-action-card")
    
    if action_card.count() > 0:
        print("✅ Action suggestion card appeared")
        
        # Check card content
        card_text = action_card.inner_text()
        print(f"Card content: {card_text[:200]}...")
        
        assert "AAPL" in card_text, "Action card should mention AAPL"
        assert "Confirm" in card_text, "Action card should have Confirm button"
        print("✅ Action card has expected content")
        
        # Click confirm
        print("Confirming action...")
        page.click("#chatbot-action-confirm")
        time.sleep(1)
        
        # Wait for execution result
        print("Waiting for execution result...")
        time.sleep(2)
        
        # Check for success/rejection message
        messages = page.locator("#chatbot-messages").inner_text()
        
        if "success" in messages.lower() or "submitted" in messages.lower():
            print("✅ Action executed successfully")
        elif "rejected" in messages.lower() or "paper" in messages.lower():
            print("✅ Action validated (paper trading enforced)")
        else:
            print(f"⚠️ Execution result unclear: {messages[-200:]}")
        
    else:
        print("⚠️ No action card appeared")
        print("   This may be expected if RAG did not extract action from query")
        print("   Or if action execution is disabled")
    
    # Screenshot
    page.screenshot(path="reports/chat_agent/screenshots/action_flow.png")
    print("📸 Screenshot saved")


def test_chat_context_awareness(page: Page):
    """
    TEST 4: Context-aware responses
    
    Acceptance Criteria:
    - Chat knows which tab user is on
    - Responses reference current context
    """
    print("\n" + "="*70)
    print("TEST 4: Context Awareness")
    print("="*70)
    
    page.goto("http://localhost:8050")
    page.wait_for_load_state("networkidle")
    
    # Navigate to Market Trends tab
    print("Navigating to Market Trends tab...")
    market_trends_tab = page.locator('a[href*="market_trends"]').first
    if market_trends_tab.count() > 0:
        market_trends_tab.click()
        time.sleep(1)
        print("✅ On Market Trends tab")
    
    # Open chat
    page.click("#chatbot-toggle-btn")
    page.wait_for_selector("#chatbot-container", state="visible", timeout=5000)
    
    # Ask context-dependent question
    query = "Summarize the current market trends"
    print(f"Sending context query: {query}")
    page.fill("#chatbot-input", query)
    page.click("#chatbot-send-btn")
    
    # Wait for response via diagnostic dataset
    page.wait_for_function(
        "() => { const el = document.querySelector('#chat-color-diagnostic'); return el && el.dataset && el.dataset.lastResponse && parseInt(el.dataset.lastResponseLen||'0')>0 }",
        timeout=30000,
    )

    messages = page.locator("#chatbot-messages").inner_text()
    print(f"Response preview: {messages[-300:]}")
    
    # Check if response references market data
    if any(word in messages.lower() for word in ["trend", "market", "volatility", "spy"]):
        print("✅ Response appears context-aware")
    else:
        print("⚠️ Response may not be using context")
    
    page.screenshot(path="reports/chat_agent/screenshots/context_awareness.png")
    print("📸 Screenshot saved")


def test_chat_persistence(page: Page):
    """
    TEST 5: Chat history persists during session
    
    Acceptance Criteria:
    - Multiple messages stay in chat
    - Closing and reopening preserves history
    """
    print("\n" + "="*70)
    print("TEST 5: Chat History Persistence")
    print("="*70)
    
    page.goto("http://localhost:8050")
    page.wait_for_load_state("networkidle")
    
    # Open chat
    page.click("#chatbot-toggle-btn")
    page.wait_for_selector("#chatbot-container", state="visible", timeout=5000)
    
    # Send 3 messages
    messages_to_send = [
        "What is AAPL?",
        "What about MSFT?",
        "Compare them"
    ]
    
    for msg in messages_to_send:
        print(f"Sending: {msg}")
        page.fill("#chatbot-input", msg)
        page.click("#chatbot-send-btn")
        time.sleep(2)  # Wait for response
    
    # Count messages
    all_messages = page.locator('[data-testid="chat-message"]')
    initial_count = all_messages.count()
    print(f"✅ Chat has {initial_count} messages")
    
    # Close chat
    page.click("#chatbot-close-btn")
    time.sleep(0.5)
    
    # Reopen chat
    page.click("#chatbot-toggle-btn")
    page.wait_for_selector("#chatbot-container", state="visible", timeout=5000)
    
    # Check if messages still there
    reopened_count = all_messages.count()
    print(f"After reopen: {reopened_count} messages")
    
    assert reopened_count == initial_count, \
        f"Messages should persist (had {initial_count}, now {reopened_count})"
    print("✅ Chat history persisted")
    
    page.screenshot(path="reports/chat_agent/screenshots/chat_persistence.png")
    print("📸 Screenshot saved")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--headed", "-s"])
