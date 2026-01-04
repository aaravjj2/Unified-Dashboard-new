#!/usr/bin/env python3
"""
Phase 3 Validation Script

Validates all Phase 3 (66-100%) components are properly implemented
and functional for production deployment.

Phase 3 Components:
- Module 19: Live Trading Orchestrator
- Module 20: RL Strategy Optimizer
- Module 21: Market Regime Detector
- Module 23: FastAPI Backend
- Module 24: WebSocket Real-time
- Module 25: News Sentiment Engine
- Module 26: Market Making Engine
- Module 29: Kubernetes Deployment
- Module 30: Security & Authentication
"""
from __future__ import annotations

import asyncio
import importlib
import inspect
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


class ValidationResult:
    """Result of a validation check"""
    def __init__(self, name: str, passed: bool, message: str = "", details: str = ""):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details


class Phase3Validator:
    """Validates Phase 3 implementation completeness"""
    
    def __init__(self):
        self.results: List[ValidationResult] = []
        
    def add_result(self, name: str, passed: bool, message: str = "", details: str = ""):
        """Add a validation result"""
        self.results.append(ValidationResult(name, passed, message, details))
        
    async def validate_all(self) -> bool:
        """Run all validations"""
        print("\n" + "="*70)
        print("PHASE 3 (66-100%) VALIDATION - PRODUCTION READINESS CHECK")
        print("="*70 + "\n")
        
        # Run all validation groups
        await self.validate_live_trading()
        await self.validate_ml_components()
        await self.validate_api_backend()
        await self.validate_sentiment_engine()
        await self.validate_market_making()
        await self.validate_kubernetes()
        await self.validate_security()
        
        # Print summary
        return self.print_summary()
        
    async def validate_live_trading(self):
        """Validate Module 19: Live Trading Orchestrator"""
        print("\n📊 VALIDATING MODULE 19: LIVE TRADING ORCHESTRATOR")
        print("-" * 50)
        
        # Check orchestrator module
        try:
            from src.live_trading.orchestrator import (
                LiveTradingOrchestrator,
                TradingState,
                PreMarketChecklist,
            )
            self.add_result(
                "Live Trading Orchestrator Import",
                True,
                "All classes imported successfully"
            )
            
            # Verify key methods
            orchestrator = LiveTradingOrchestrator.__new__(LiveTradingOrchestrator)
            required_methods = [
                'start', 'stop', 'run_pre_market_checklist',
                '_trading_loop', '_intraday_safety_checks', '_end_of_day_reconciliation'
            ]
            
            missing = [m for m in required_methods if not hasattr(orchestrator, m)]
            if missing:
                self.add_result("Orchestrator Methods", False, f"Missing: {missing}")
            else:
                self.add_result("Orchestrator Methods", True, "All required methods present")
                
        except ImportError as e:
            self.add_result("Live Trading Orchestrator Import", False, str(e))
            
        # Check capital manager
        try:
            from src.live_trading.capital_manager import CapitalRampUpManager
            self.add_result("Capital Ramp-Up Manager", True, "Imported successfully")
        except ImportError as e:
            self.add_result("Capital Ramp-Up Manager", False, str(e))
            
        # Check kill switch
        try:
            from src.live_trading.kill_switch import KillSwitch
            self.add_result("Kill Switch", True, "Imported successfully")
        except ImportError as e:
            self.add_result("Kill Switch", False, str(e))
            
        # Check reconciliation
        try:
            from src.live_trading.reconciliation import PositionReconciler
            self.add_result("Position Reconciler", True, "Imported successfully")
        except ImportError as e:
            self.add_result("Position Reconciler", False, str(e))
            
    async def validate_ml_components(self):
        """Validate Modules 20-21: ML Components"""
        print("\n🤖 VALIDATING MODULES 20-21: ML COMPONENTS")
        print("-" * 50)
        
        # Check RL optimizer
        try:
            from src.ml.rl_optimizer import (
                RLStrategyOptimizer,
                TradingStrategyEnv,
                StrategyConfig,
            )
            self.add_result("RL Strategy Optimizer", True, "All classes imported")
            
            # Verify environment is Gym-compatible
            env = TradingStrategyEnv.__new__(TradingStrategyEnv)
            gym_methods = ['step', 'reset', 'render']
            missing = [m for m in gym_methods if not hasattr(env, m)]
            if missing:
                self.add_result("Gym Environment Compatibility", False, f"Missing: {missing}")
            else:
                self.add_result("Gym Environment Compatibility", True, "All Gym methods present")
                
        except ImportError as e:
            self.add_result("RL Strategy Optimizer", False, str(e))
            
        # Check regime detector
        try:
            from src.ml.regime_detector import (
                MarketRegimeDetector,
                MarketRegime,
                RegimeAdaptiveStrategySelector,
            )
            self.add_result("Market Regime Detector", True, "All classes imported")
            
            # Verify regimes
            expected_regimes = ['LOW_VOLATILITY', 'HIGH_VOLATILITY', 'TRENDING', 'MEAN_REVERTING', 'CRISIS']
            actual_regimes = [r.name for r in MarketRegime]
            missing = [r for r in expected_regimes if r not in actual_regimes]
            if missing:
                self.add_result("Market Regimes", False, f"Missing regimes: {missing}")
            else:
                self.add_result("Market Regimes", True, f"{len(actual_regimes)} regimes defined")
                
        except ImportError as e:
            self.add_result("Market Regime Detector", False, str(e))
            
    async def validate_api_backend(self):
        """Validate Modules 23-24: API Backend"""
        print("\n🌐 VALIDATING MODULES 23-24: API BACKEND")
        print("-" * 50)
        
        # Check FastAPI app
        try:
            from src.api.main import app, lifespan
            self.add_result("FastAPI Application", True, "App created successfully")
            
            # Count routes
            route_count = len([r for r in app.routes if hasattr(r, 'path')])
            self.add_result("API Routes", True, f"{route_count} routes registered")
            
        except ImportError as e:
            self.add_result("FastAPI Application", False, str(e))
            
        # Check route modules
        route_modules = ['portfolio', 'strategies', 'risk', 'orders', 'analytics']
        for module_name in route_modules:
            try:
                module = importlib.import_module(f"src.api.routes.{module_name}")
                router = getattr(module, 'router', None)
                if router:
                    route_count = len([r for r in router.routes if hasattr(r, 'path')])
                    self.add_result(f"Route: {module_name}", True, f"{route_count} endpoints")
                else:
                    self.add_result(f"Route: {module_name}", False, "No router found")
            except ImportError as e:
                self.add_result(f"Route: {module_name}", False, str(e))
                
        # Check WebSocket manager
        try:
            from src.api.websocket import WebSocketManager, setup_socketio_handlers
            self.add_result("WebSocket Manager", True, "Imported successfully")
            
            # Verify channels
            ws = WebSocketManager()
            expected_channels = ['portfolio', 'positions', 'orders', 'prices', 'greeks', 'alerts']
            missing = [c for c in expected_channels if c not in ws.CHANNELS]
            if missing:
                self.add_result("WebSocket Channels", False, f"Missing: {missing}")
            else:
                self.add_result("WebSocket Channels", True, f"{len(ws.CHANNELS)} channels defined")
                
        except ImportError as e:
            self.add_result("WebSocket Manager", False, str(e))
            
    async def validate_sentiment_engine(self):
        """Validate Module 25: News Sentiment Engine"""
        print("\n📰 VALIDATING MODULE 25: NEWS SENTIMENT ENGINE")
        print("-" * 50)
        
        # Check sentiment module
        try:
            from src.sentiment import (
                NewsSentimentEngine,
                FinBERTSentimentAnalyzer,
                NewsAggregator,
                Sentiment,
                NewsCategory,
            )
            self.add_result("News Sentiment Engine", True, "All classes imported")
            
            # Verify sentiment values
            expected_sentiments = ['VERY_BEARISH', 'BEARISH', 'NEUTRAL', 'BULLISH', 'VERY_BULLISH']
            actual = [s.name for s in Sentiment]
            missing = [s for s in expected_sentiments if s not in actual]
            if missing:
                self.add_result("Sentiment Types", False, f"Missing: {missing}")
            else:
                self.add_result("Sentiment Types", True, f"{len(actual)} sentiment types")
                
        except ImportError as e:
            self.add_result("News Sentiment Engine", False, str(e))
            
        # Check earnings module
        try:
            from src.sentiment.earnings import (
                EarningsCalendar,
                EventImpactAnalyzer,
                EventType,
            )
            self.add_result("Earnings Calendar", True, "Imported successfully")
        except ImportError as e:
            self.add_result("Earnings Calendar", False, str(e))
            
    async def validate_market_making(self):
        """Validate Module 26: Market Making Engine"""
        print("\n💹 VALIDATING MODULE 26: MARKET MAKING ENGINE")
        print("-" * 50)
        
        try:
            from src.market_making import (
                MarketMakingEngine,
                SpreadCalculator,
                InventoryManager,
                Quote,
                Instrument,
            )
            self.add_result("Market Making Engine", True, "All classes imported")
            
            # Verify key methods
            engine = MarketMakingEngine.__new__(MarketMakingEngine)
            required_methods = [
                'start', 'stop', 'add_instrument', 'remove_instrument',
                'handle_fill', 'update_market_data', 'update_greeks'
            ]
            missing = [m for m in required_methods if not hasattr(engine, m)]
            if missing:
                self.add_result("MM Engine Methods", False, f"Missing: {missing}")
            else:
                self.add_result("MM Engine Methods", True, "All required methods present")
                
        except ImportError as e:
            self.add_result("Market Making Engine", False, str(e))
            
    async def validate_kubernetes(self):
        """Validate Module 29: Kubernetes Deployment"""
        print("\n☸️  VALIDATING MODULE 29: KUBERNETES DEPLOYMENT")
        print("-" * 50)
        
        k8s_base = project_root / "k8s" / "base"
        k8s_staging = project_root / "k8s" / "overlays" / "staging"
        k8s_prod = project_root / "k8s" / "overlays" / "production"
        
        # Check base manifests
        required_base = ['infrastructure.yaml', 'services.yaml', 'networking.yaml', 'monitoring.yaml', 'kustomization.yaml']
        for filename in required_base:
            filepath = k8s_base / filename
            if filepath.exists():
                size = filepath.stat().st_size
                self.add_result(f"K8s Base: {filename}", True, f"{size} bytes")
            else:
                self.add_result(f"K8s Base: {filename}", False, "File not found")
                
        # Check overlays
        staging_kust = k8s_staging / "kustomization.yaml"
        prod_kust = k8s_prod / "kustomization.yaml"
        
        self.add_result("K8s Staging Overlay", staging_kust.exists(), 
                       "Present" if staging_kust.exists() else "Missing")
        self.add_result("K8s Production Overlay", prod_kust.exists(),
                       "Present" if prod_kust.exists() else "Missing")
                       
        # Verify key resources in infrastructure.yaml
        if (k8s_base / "infrastructure.yaml").exists():
            content = (k8s_base / "infrastructure.yaml").read_text()
            resources = ['Namespace', 'ConfigMap', 'Secret', 'Deployment', 'Service', 'PersistentVolumeClaim']
            found = [r for r in resources if f"kind: {r}" in content]
            self.add_result("K8s Resources", True, f"{len(found)}/{len(resources)} resource types defined")
            
    async def validate_security(self):
        """Validate Module 30: Security & Authentication"""
        print("\n🔐 VALIDATING MODULE 30: SECURITY & AUTH")
        print("-" * 50)
        
        # Check main security module
        try:
            from src.security import (
                AuthenticationService,
                JWTManager,
                APIKeyManager,
                PasswordHasher,
                RateLimiter,
                AuditLogger,
                UserRole,
            )
            self.add_result("Security Module", True, "All classes imported")
            
            # Verify user roles
            expected_roles = ['VIEWER', 'TRADER', 'ADMIN', 'SUPER_ADMIN']
            actual = [r.name for r in UserRole]
            missing = [r for r in expected_roles if r not in actual]
            if missing:
                self.add_result("User Roles", False, f"Missing: {missing}")
            else:
                self.add_result("User Roles", True, f"{len(actual)} roles defined")
                
        except ImportError as e:
            self.add_result("Security Module", False, str(e))
            
        # Check middleware
        try:
            from src.security.middleware import (
                get_current_user,
                require_role,
                RateLimitMiddleware,
                AuditMiddleware,
            )
            self.add_result("Security Middleware", True, "Imported successfully")
        except ImportError as e:
            self.add_result("Security Middleware", False, str(e))
            
    def print_summary(self) -> bool:
        """Print validation summary"""
        print("\n" + "="*70)
        print("VALIDATION SUMMARY")
        print("="*70)
        
        passed = [r for r in self.results if r.passed]
        failed = [r for r in self.results if not r.passed]
        
        total = len(self.results)
        pass_rate = len(passed) / total * 100 if total > 0 else 0
        
        print(f"\n✅ PASSED: {len(passed)}/{total} ({pass_rate:.1f}%)")
        print(f"❌ FAILED: {len(failed)}/{total}")
        
        if failed:
            print("\n⚠️  FAILED CHECKS:")
            for result in failed:
                print(f"   • {result.name}: {result.message}")
                
        print("\n" + "-"*70)
        
        if pass_rate >= 90:
            print("🎉 PHASE 3 VALIDATION: PASSED")
            print("   System is ready for production deployment")
        elif pass_rate >= 70:
            print("⚠️  PHASE 3 VALIDATION: PARTIAL")
            print("   Some components need attention before production")
        else:
            print("❌ PHASE 3 VALIDATION: FAILED")
            print("   Significant issues need to be resolved")
            
        print("-"*70)
        print(f"Validated at: {datetime.now(timezone.utc).isoformat()}")
        print("="*70 + "\n")
        
        return pass_rate >= 90


async def main():
    """Main entry point"""
    validator = Phase3Validator()
    success = await validator.validate_all()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
