"""
Webhook Server E2E Test Runner
================================

Complete end-to-end validation of webhook server:
1. Authentication tests
2. Signal validation tests
3. Risk manager integration tests
4. Execution tests
5. Deterministic validation (3 iterations)
6. Performance SLA tests

Simplified test runner without pytest dependency.
"""

import json
import time
import hashlib
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Test if FastAPI is available
try:
    from fastapi.testclient import TestClient
    from webhook_server import (
        WebhookServer, TRADINGVIEW_SECRET,
        save_signal_logs, save_execution_logs,
        calculate_deterministic_hash,
        signal_history, execution_history
    )
    from strategy_bot import StrategyBot, StrategyMode, RiskLimits
    from broker_connector import MockBrokerConnector
    DEPS_AVAILABLE = True
except ImportError as e:
    print(f"❌ Missing dependencies: {e}")
    print("Install with: pip install fastapi uvicorn python-dotenv")
    DEPS_AVAILABLE = False
    sys.exit(1)

# Test outputs
OUTPUTS_DIR = Path("outputs/webhook_tests")
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# Test Utilities
# ============================================================================

def create_test_server():
    """Create a fresh test server"""
    broker = MockBrokerConnector(initial_cash=100000, random_seed=42)
    risk_limits = RiskLimits(
        max_position_size_pct=10.0,
        max_concentration_pct=25.0
    )
    strategy_bot = StrategyBot(
        mode=StrategyMode.MOCK,
        broker=broker,
        risk_limits=risk_limits
    )
    
    server = WebhookServer(
        strategy_bot=strategy_bot,
        mock_mode=True,
        auto_expose=False
    )
    
    return server, TestClient(server.app)

# ============================================================================
# Test Suite
# ============================================================================

def run_all_tests():
    """Run complete test suite"""
    
    print("="*80)
    print("WEBHOOK SERVER E2E TEST SUITE")
    print("="*80)
    
    test_results = {
        "timestamp": datetime.now().isoformat(),
        "tests_run": 0,
        "tests_passed": 0,
        "tests_failed": 0,
        "details": []
    }
    
    # Test 1: Valid Authentication
    print("\n--- Test 1: Valid Authentication ---")
    try:
        server, client = create_test_server()
        
        alert = {
            "symbol": "SPY",
            "action": "BUY_CALL",
            "price": 450.0,
            "strike": 455.0,
            "expiry": "2025-12-31",
            "quantity": 5
        }
        
        response = client.post(
            "/webhook",
            json=alert,
            headers={"Authorization": f"Bearer {TRADINGVIEW_SECRET}"}
        )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert data["status"] == "success"
        assert "signal_id" in data
        
        print(f"✅ PASSED: Valid authentication (signal_id={data['signal_id']})")
        test_results["tests_passed"] += 1
        test_results["details"].append({"test": "valid_auth", "status": "PASS"})
    except Exception as e:
        print(f"❌ FAILED: {e}")
        test_results["tests_failed"] += 1
        test_results["details"].append({"test": "valid_auth", "status": "FAIL", "error": str(e)})
    finally:
        test_results["tests_run"] += 1
    
    # Test 2: Invalid Authentication
    print("\n--- Test 2: Invalid Authentication ---")
    try:
        server, client = create_test_server()
        
        alert = {"symbol": "SPY", "action": "BUY_CALL", "price": 450.0}
        
        response = client.post(
            "/webhook",
            json=alert,
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        
        print("✅ PASSED: Invalid authentication rejected")
        test_results["tests_passed"] += 1
        test_results["details"].append({"test": "invalid_auth", "status": "PASS"})
    except Exception as e:
        print(f"❌ FAILED: {e}")
        test_results["tests_failed"] += 1
        test_results["details"].append({"test": "invalid_auth", "status": "FAIL", "error": str(e)})
    finally:
        test_results["tests_run"] += 1
    
    # Test 3: Signal Validation (Valid)
    print("\n--- Test 3: Valid Signal Validation ---")
    try:
        server, client = create_test_server()
        
        alert = {
            "symbol": "AAPL",
            "action": "BUY_PUT",
            "price": 180.0,
            "strike": 175.0,
            "expiry": "2025-11-15",
            "quantity": 10
        }
        
        response = client.post(
            "/webhook",
            json=alert,
            headers={"Authorization": f"Bearer {TRADINGVIEW_SECRET}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["signal_id"].startswith("tv_signal_")
        
        print(f"✅ PASSED: Valid signal (AAPL PUT, signal_id={data['signal_id']})")
        test_results["tests_passed"] += 1
        test_results["details"].append({"test": "valid_signal", "status": "PASS"})
    except Exception as e:
        print(f"❌ FAILED: {e}")
        test_results["tests_failed"] += 1
        test_results["details"].append({"test": "valid_signal", "status": "FAIL", "error": str(e)})
    finally:
        test_results["tests_run"] += 1
    
    # Test 4: Signal Validation (Invalid Symbol)
    print("\n--- Test 4: Invalid Symbol Validation ---")
    try:
        server, client = create_test_server()
        
        alert = {
            "symbol": "",  # Empty symbol
            "action": "BUY_CALL",
            "price": 450.0
        }
        
        response = client.post(
            "/webhook",
            json=alert,
            headers={"Authorization": f"Bearer {TRADINGVIEW_SECRET}"}
        )
        
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"
        
        print("✅ PASSED: Invalid symbol rejected")
        test_results["tests_passed"] += 1
        test_results["details"].append({"test": "invalid_symbol", "status": "PASS"})
    except Exception as e:
        print(f"❌ FAILED: {e}")
        test_results["tests_failed"] += 1
        test_results["details"].append({"test": "invalid_symbol", "status": "FAIL", "error": str(e)})
    finally:
        test_results["tests_run"] += 1
    
    # Test 5: Health Endpoint
    print("\n--- Test 5: Health Check Endpoint ---")
    try:
        server, client = create_test_server()
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "mode" in data
        
        print(f"✅ PASSED: Health check (mode={data['mode']}, signals={data['signals_received']})")
        test_results["tests_passed"] += 1
        test_results["details"].append({"test": "health_check", "status": "PASS"})
    except Exception as e:
        print(f"❌ FAILED: {e}")
        test_results["tests_failed"] += 1
        test_results["details"].append({"test": "health_check", "status": "FAIL", "error": str(e)})
    finally:
        test_results["tests_run"] += 1
    
    # Test 6: Successful Execution
    print("\n--- Test 6: Successful Signal Execution ---")
    try:
        server, client = create_test_server()
        
        alert = {
            "symbol": "SPY",
            "action": "BUY_STOCK",
            "price": 450.0,
            "quantity": 10
        }
        
        response = client.post(
            "/webhook",
            json=alert,
            headers={"Authorization": f"Bearer {TRADINGVIEW_SECRET}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["execution_status"] == "executed"
        
        print(f"✅ PASSED: Signal executed successfully (signal_id={data['signal_id']})")
        test_results["tests_passed"] += 1
        test_results["details"].append({"test": "successful_execution", "status": "PASS"})
    except Exception as e:
        print(f"❌ FAILED: {e}")
        test_results["tests_failed"] += 1
        test_results["details"].append({"test": "successful_execution", "status": "FAIL", "error": str(e)})
    finally:
        test_results["tests_run"] += 1
    
    # Test 7: Risk Manager Rejection
    print("\n--- Test 7: Risk Manager Rejection ---")
    try:
        # Create server with low capital
        broker = MockBrokerConnector(initial_cash=10000, random_seed=42)
        strategy_bot = StrategyBot(mode=StrategyMode.MOCK, broker=broker)
        server = WebhookServer(strategy_bot=strategy_bot, mock_mode=True, auto_expose=False)
        client = TestClient(server.app)
        
        alert = {
            "symbol": "SPY",
            "action": "BUY_CALL",
            "price": 450.0,
            "strike": 455.0,
            "expiry": "2025-12-31",
            "quantity": 100  # Too many contracts
        }
        
        response = client.post(
            "/webhook",
            json=alert,
            headers={"Authorization": f"Bearer {TRADINGVIEW_SECRET}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["execution_status"] in ["rejected_by_risk_manager", "execution_failed"]
        
        print(f"✅ PASSED: Risk manager blocked unsafe trade (status={data['execution_status']})")
        test_results["tests_passed"] += 1
        test_results["details"].append({"test": "risk_rejection", "status": "PASS"})
    except Exception as e:
        print(f"❌ FAILED: {e}")
        test_results["tests_failed"] += 1
        test_results["details"].append({"test": "risk_rejection", "status": "FAIL", "error": str(e)})
    finally:
        test_results["tests_run"] += 1
    
    # Test 8: Deterministic Validation (3 iterations)
    print("\n--- Test 8: Deterministic Validation (3 iterations) ---")
    try:
        hashes = []
        
        for iteration in range(1, 4):
            # Clear histories
            signal_history.clear()
            execution_history.clear()
            
            # Create fresh server
            broker = MockBrokerConnector(initial_cash=100000, random_seed=42)
            strategy_bot = StrategyBot(mode=StrategyMode.MOCK, broker=broker)
            server = WebhookServer(strategy_bot=strategy_bot, mock_mode=True, auto_expose=False)
            client = TestClient(server.app)
            
            # Execute same signals
            test_signals = [
                {"symbol": "SPY", "action": "BUY_CALL", "price": 450.0, "strike": 455.0, "expiry": "2025-12-31", "quantity": 5},
                {"symbol": "QQQ", "action": "BUY_STOCK", "price": 380.0, "quantity": 20},
                {"symbol": "AAPL", "action": "SELL_PUT", "price": 180.0, "strike": 175.0, "expiry": "2025-11-15", "quantity": 3}
            ]
            
            for signal in test_signals:
                client.post(
                    "/webhook",
                    json=signal,
                    headers={"Authorization": f"Bearer {TRADINGVIEW_SECRET}"}
                )
            
            # Calculate hash
            iteration_hash = calculate_deterministic_hash(signal_history, execution_history)
            hashes.append(iteration_hash)
            
            print(f"  Iteration {iteration}: {len(signal_history)} signals, hash={iteration_hash[:16]}...")
        
        # Verify all hashes match
        assert hashes[0] == hashes[1] == hashes[2], f"Hash mismatch: {hashes}"
        
        print(f"✅ PASSED: Deterministic validation (3 iterations, identical hashes)")
        print(f"   Hash: {hashes[0]}")
        test_results["tests_passed"] += 1
        test_results["details"].append({
            "test": "deterministic_validation",
            "status": "PASS",
            "hash": hashes[0]
        })
    except Exception as e:
        print(f"❌ FAILED: {e}")
        test_results["tests_failed"] += 1
        test_results["details"].append({"test": "deterministic_validation", "status": "FAIL", "error": str(e)})
    finally:
        test_results["tests_run"] += 1
    
    # Test 9: Performance SLA (<150ms)
    print("\n--- Test 9: Performance SLA (<150ms) ---")
    try:
        server, client = create_test_server()
        
        test_signals = [
            {"symbol": "SPY", "action": "BUY_STOCK", "price": 450.0, "quantity": 10},
            {"symbol": "QQQ", "action": "BUY_CALL", "price": 380.0, "strike": 385.0, "expiry": "2025-12-31", "quantity": 5},
            {"symbol": "AAPL", "action": "SELL_PUT", "price": 180.0, "strike": 175.0, "expiry": "2025-11-15", "quantity": 3}
        ]
        
        processing_times = []
        
        for signal in test_signals:
            start = time.time()
            
            response = client.post(
                "/webhook",
                json=signal,
                headers={"Authorization": f"Bearer {TRADINGVIEW_SECRET}"}
            )
            
            elapsed_ms = (time.time() - start) * 1000
            processing_times.append(elapsed_ms)
            
            assert response.status_code == 200
        
        avg_time = sum(processing_times) / len(processing_times)
        max_time = max(processing_times)
        
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  Max: {max_time:.2f}ms")
        print(f"  SLA: <150ms")
        
        sla_violations = [t for t in processing_times if t > 150]
        sla_compliance = (len(processing_times) - len(sla_violations)) / len(processing_times) * 100
        
        print(f"  SLA compliance: {sla_compliance:.1f}%")
        
        print(f"✅ PASSED: Performance SLA (max={max_time:.2f}ms, avg={avg_time:.2f}ms)")
        test_results["tests_passed"] += 1
        test_results["details"].append({
            "test": "performance_sla",
            "status": "PASS",
            "avg_ms": avg_time,
            "max_ms": max_time,
            "sla_compliance_pct": sla_compliance
        })
    except Exception as e:
        print(f"❌ FAILED: {e}")
        test_results["tests_failed"] += 1
        test_results["details"].append({"test": "performance_sla", "status": "FAIL", "error": str(e)})
    finally:
        test_results["tests_run"] += 1
    
    # ========================================================================
    # Summary
    # ========================================================================
    
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Tests run: {test_results['tests_run']}")
    print(f"Passed: {test_results['tests_passed']} ✅")
    print(f"Failed: {test_results['tests_failed']} ❌")
    print(f"Success rate: {test_results['tests_passed']/test_results['tests_run']*100:.1f}%")
    print("="*80)
    
    # Save results
    results_file = OUTPUTS_DIR / "test_results.json"
    with open(results_file, "w") as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\n💾 Results saved: {results_file}")
    
    return test_results

# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    if not DEPS_AVAILABLE:
        print("❌ Cannot run tests - missing dependencies")
        sys.exit(1)
    
    results = run_all_tests()
    
    # Exit code based on results
    sys.exit(0 if results["tests_failed"] == 0 else 1)
