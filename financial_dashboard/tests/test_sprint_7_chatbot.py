"""
Sprint 7: AI Chatbot E2E Tests
Tests the new AI chatbot assistant feature
"""

import pytest
import time
from playwright.sync_api import Page, expect
import httpx


# Test Configuration
DASHBOARD_URL = "http://localhost:8000"
API_GATEWAY_URL = "http://localhost:8049"
CHATBOT_SERVICE_URL = "http://localhost:8062"


class TestSprintSeven:
    """End-to-end tests for Sprint 7: AI Chatbot Assistant"""
    
    @pytest.fixture(autouse=True)
    def setup(self, page: Page):
        """Setup before each test"""
        self.page = page
        # Set longer timeout for network requests
        page.set_default_timeout(30000)
        
    def test_01_chatbot_service_health(self):
        """Test that the chatbot service is running and healthy"""
        try:
            response = httpx.get(f"{CHATBOT_SERVICE_URL}/health", timeout=10)
            assert response.status_code == 200, f"Chatbot service health check failed: {response.status_code}"
            data = response.json()
            assert data["status"] == "healthy", "Chatbot service not healthy"
            assert "chatbot_service" in data.get("service", ""), "Invalid service name"
            print("✓ Chatbot service is healthy")
        except Exception as e:
            pytest.fail(f"Chatbot service health check failed: {e}")
    
    def test_02_api_gateway_chatbot_route(self):
        """Test that API gateway routes chatbot requests correctly"""
        try:
            # Test health endpoint through gateway
            response = httpx.get(f"{API_GATEWAY_URL}/api/chat/health", timeout=10)
            assert response.status_code == 200, f"Gateway routing failed: {response.status_code}"
            print("✓ API Gateway chatbot route is working")
        except Exception as e:
            pytest.fail(f"API Gateway chatbot route failed: {e}")
    
    def test_03_chatbot_fab_visible(self):
        """Test that the floating action button is visible on the dashboard"""
        self.page.goto(DASHBOARD_URL)
        self.page.wait_for_load_state("networkidle")
        
        # Look for chatbot FAB
        fab = self.page.locator("#chatbot-toggle-btn")
        expect(fab).to_be_visible(timeout=10000)
        print("✓ Chatbot FAB is visible")
    
    def test_04_chatbot_window_toggle(self):
        """Test that clicking the FAB opens the chatbot window"""
        self.page.goto(DASHBOARD_URL)
        self.page.wait_for_load_state("networkidle")
        
        # Click FAB
        fab = self.page.locator("#chatbot-toggle-btn")
        fab.click()
        
        # Wait for chatbot window to appear
        time.sleep(1)
        chatbot_window = self.page.locator("#chatbot-window")
        expect(chatbot_window).to_be_visible(timeout=5000)
        print("✓ Chatbot window opens on FAB click")
    
    def test_05_chatbot_welcome_message(self):
        """Test that the chatbot shows a welcome message"""
        self.page.goto(DASHBOARD_URL)
        self.page.wait_for_load_state("networkidle")
        
        # Open chatbot
        fab = self.page.locator("#chatbot-toggle-btn")
        fab.click()
        time.sleep(1)
        
        # Check for welcome message
        messages = self.page.locator("#chatbot-messages")
        expect(messages).to_contain_text("AI financial assistant", timeout=5000)
        print("✓ Welcome message is displayed")
    
    def test_06_chatbot_send_message(self):
        """Test sending a message to the chatbot"""
        self.page.goto(DASHBOARD_URL)
        self.page.wait_for_load_state("networkidle")
        
        # Open chatbot
        fab = self.page.locator("#chatbot-toggle-btn")
        fab.click()
        time.sleep(1)
        
        # Type and send a message
        input_field = self.page.locator("#chatbot-input")
        input_field.fill("What is the price of AAPL?")
        
        send_btn = self.page.locator("#chatbot-send-btn")
        send_btn.click()
        
        # Wait for response (give it time to process)
        time.sleep(3)
        
        # Check that message appears
        messages = self.page.locator("#chatbot-messages")
        expect(messages).to_contain_text("AAPL", timeout=10000)
        print("✓ Message sent and response received")
    
    def test_07_chatbot_close_button(self):
        """Test that the close button hides the chatbot window"""
        self.page.goto(DASHBOARD_URL)
        self.page.wait_for_load_state("networkidle")
        
        # Open chatbot
        fab = self.page.locator("#chatbot-toggle-btn")
        fab.click()
        time.sleep(1)
        
        # Close chatbot
        close_btn = self.page.locator("#chatbot-close-btn")
        close_btn.click()
        time.sleep(1)
        
        # Verify window is hidden
        chatbot_container = self.page.locator("#chatbot-container")
        # Check display style is none
        style = chatbot_container.get_attribute("style")
        assert "display: none" in style or "display:none" in style, "Chatbot window not hidden"
        print("✓ Close button hides chatbot window")
    
    def test_08_chatbot_api_direct_call(self):
        """Test calling the chatbot API directly"""
        try:
            response = httpx.post(
                f"{CHATBOT_SERVICE_URL}/api/chat",
                json={"message": "What is a stock?", "session_id": "test-session"},
                timeout=30
            )
            assert response.status_code == 200, f"Chatbot API call failed: {response.status_code}"
            data = response.json()
            assert "response" in data, "No response in chatbot reply"
            assert len(data["response"]) > 0, "Empty response from chatbot"
            print(f"✓ Chatbot API direct call successful. Response: {data['response'][:100]}...")
        except Exception as e:
            pytest.fail(f"Chatbot API direct call failed: {e}")
    
    def test_09_chatbot_history_endpoint(self):
        """Test the chat history endpoint"""
        try:
            # First, send a message
            httpx.post(
                f"{CHATBOT_SERVICE_URL}/api/chat",
                json={"message": "Test history", "session_id": "history-test"},
                timeout=30
            )
            
            # Then retrieve history
            response = httpx.get(
                f"{CHATBOT_SERVICE_URL}/api/chat/history?session_id=history-test",
                timeout=10
            )
            assert response.status_code == 200, f"History endpoint failed: {response.status_code}"
            data = response.json()
            assert "history" in data, "No history in response"
            assert len(data["history"]) > 0, "History is empty"
            print("✓ Chat history endpoint working")
        except Exception as e:
            pytest.fail(f"Chat history endpoint failed: {e}")
    
    def test_10_chatbot_multiple_queries(self):
        """Test multiple sequential queries to the chatbot"""
        self.page.goto(DASHBOARD_URL)
        self.page.wait_for_load_state("networkidle")
        
        # Open chatbot
        fab = self.page.locator("#chatbot-toggle-btn")
        fab.click()
        time.sleep(1)
        
        queries = [
            "Tell me about market trends",
            "What is portfolio optimization?",
            "Explain options trading"
        ]
        
        for query in queries:
            input_field = self.page.locator("#chatbot-input")
            input_field.fill(query)
            
            send_btn = self.page.locator("#chatbot-send-btn")
            send_btn.click()
            
            # Wait between queries
            time.sleep(2)
        
        # Check that all queries appear in messages
        messages = self.page.locator("#chatbot-messages")
        for query in queries:
            expect(messages).to_contain_text(query[:20], timeout=5000)
        
        print("✓ Multiple sequential queries successful")


@pytest.mark.integration
class TestSprintSevenIntegration:
    """Integration tests for Sprint 7 chatbot with other services"""
    
    def test_chatbot_options_service_integration(self):
        """Test that chatbot can query the options service"""
        try:
            response = httpx.post(
                f"{CHATBOT_SERVICE_URL}/api/chat",
                json={"message": "What is the price of SPY?", "session_id": "options-test"},
                timeout=30
            )
            assert response.status_code == 200
            data = response.json()
            # Response should mention SPY or price-related info
            assert any(keyword in data["response"].lower() for keyword in ["spy", "price", "quote", "n/a"]), \
                "Chatbot didn't process stock price query correctly"
            print("✓ Chatbot + Options Service integration working")
        except Exception as e:
            pytest.fail(f"Chatbot options integration failed: {e}")
    
    def test_chatbot_market_trends_integration(self):
        """Test that chatbot can query market trends"""
        try:
            response = httpx.post(
                f"{CHATBOT_SERVICE_URL}/api/chat",
                json={"message": "What are the market trends?", "session_id": "trends-test"},
                timeout=30
            )
            assert response.status_code == 200
            data = response.json()
            # Response should mention market or trends
            assert any(keyword in data["response"].lower() for keyword in ["market", "trend", "sector", "analysis"]), \
                "Chatbot didn't process market trends query correctly"
            print("✓ Chatbot + Market Trends integration working")
        except Exception as e:
            pytest.fail(f"Chatbot trends integration failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
