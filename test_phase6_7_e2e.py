"""
Comprehensive End-to-End Test Suite
Phase 6 & 7 Complete Validation

Tests all new components:
- Trade Journal
- Keyboard Shortcuts
- Export Utilities
- Layout Presets
- Greeks Timeseries
- Accessibility
- Session Summary
- Backtest Engine
- Strategy Analysis
- CLI Tools
"""

import sys
import os
import time
import json
import subprocess
import requests
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"

def print_header(text: str):
    """Print section header."""
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}{BLUE}{text.center(60)}{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}\n")

def print_pass(test: str):
    """Print passed test."""
    print(f"  {GREEN}✓{RESET} {test}")

def print_fail(test: str, error: str = ""):
    """Print failed test."""
    print(f"  {RED}✗{RESET} {test}")
    if error:
        print(f"    {RED}Error: {error}{RESET}")

def print_warn(text: str):
    """Print warning."""
    print(f"  {YELLOW}⚠{RESET} {text}")


class EndToEndTestSuite:
    """Comprehensive E2E test suite."""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.results = []
    
    def run_all_tests(self):
        """Run all test categories."""
        print_header("ALPACA OPTIONS LAB - E2E TEST SUITE")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # Test categories
        test_methods = [
            ("Phase 6: Trade Journal Component", self.test_trade_journal),
            ("Phase 6: Keyboard Shortcuts", self.test_keyboard_shortcuts),
            ("Phase 6: Export Utilities", self.test_export_utils),
            ("Phase 6: Layout Presets", self.test_layout_presets),
            ("Phase 6: Greeks Timeseries", self.test_greeks_timeseries),
            ("Phase 6: Accessibility", self.test_accessibility),
            ("Phase 6: Session Summary", self.test_session_summary),
            ("Phase 7: Backtest Engine", self.test_backtest_engine),
            ("Phase 7: Monte Carlo", self.test_monte_carlo),
            ("Phase 7: Walk-Forward", self.test_walk_forward),
            ("Phase 7: Strategy Analysis", self.test_strategy_analysis),
            ("Phase 8: CLI Tools", self.test_cli_tools),
            ("Integration: Server Health", self.test_server_health),
            ("Integration: Component Imports", self.test_component_imports),
        ]
        
        for name, test_fn in test_methods:
            print_header(name)
            try:
                test_fn()
            except Exception as e:
                print_fail(f"Test suite failed: {e}")
                self.failed += 1
        
        # Print summary
        self.print_summary()
    
    def test_trade_journal(self):
        """Test trade journal component."""
        try:
            from financial_dashboard.components.trade_journal import (
                create_trade_journal_panel,
                create_pnl_attribution_panel,
            )
            
            # Test panel creation
            panel = create_trade_journal_panel()
            assert panel is not None, "Trade journal panel is None"
            print_pass("create_trade_journal_panel() returns valid component")
            self.passed += 1
            
            # Test P/L attribution
            pnl_panel = create_pnl_attribution_panel()
            assert pnl_panel is not None, "P/L attribution panel is None"
            print_pass("create_pnl_attribution_panel() returns valid component")
            self.passed += 1
            
            # Check panel has required elements
            panel_html = str(panel)
            assert "journal-table" in panel_html or "Trade Journal" in panel_html
            print_pass("Trade journal has required table element")
            self.passed += 1
            
        except Exception as e:
            print_fail(f"Trade journal test failed: {e}")
            self.failed += 1
    
    def test_keyboard_shortcuts(self):
        """Test keyboard shortcuts component."""
        try:
            from financial_dashboard.components.keyboard_shortcuts import (
                create_keyboard_shortcuts_modal,
                create_shortcuts_trigger_button,
            )
            
            modal = create_keyboard_shortcuts_modal()
            assert modal is not None
            print_pass("create_keyboard_shortcuts_modal() returns valid component")
            self.passed += 1
            
            button = create_shortcuts_trigger_button()
            assert button is not None
            print_pass("create_shortcuts_trigger_button() returns valid component")
            self.passed += 1
            
        except Exception as e:
            print_fail(f"Keyboard shortcuts test failed: {e}")
            self.failed += 1
    
    def test_export_utils(self):
        """Test export utilities component."""
        try:
            from financial_dashboard.components.export_utils import (
                create_export_dropdown,
                create_export_modal,
                create_quick_export_bar,
            )
            
            dropdown = create_export_dropdown()
            assert dropdown is not None
            print_pass("create_export_dropdown() returns valid component")
            self.passed += 1
            
            modal = create_export_modal()
            assert modal is not None
            print_pass("create_export_modal() returns valid component")
            self.passed += 1
            
            bar = create_quick_export_bar()
            assert bar is not None
            print_pass("create_quick_export_bar() returns valid component")
            self.passed += 1
            
        except Exception as e:
            print_fail(f"Export utils test failed: {e}")
            self.failed += 1
    
    def test_layout_presets(self):
        """Test layout presets component."""
        try:
            from financial_dashboard.components.layout_presets import (
                create_layout_preset_selector,
                create_layout_preset_cards,
                create_layout_customizer_modal,
                LAYOUT_PRESETS,
            )
            
            # Check presets exist
            assert len(LAYOUT_PRESETS) >= 4
            print_pass(f"LAYOUT_PRESETS has {len(LAYOUT_PRESETS)} presets")
            self.passed += 1
            
            selector = create_layout_preset_selector()
            assert selector is not None
            print_pass("create_layout_preset_selector() returns valid component")
            self.passed += 1
            
            cards = create_layout_preset_cards()
            assert cards is not None
            print_pass("create_layout_preset_cards() returns valid component")
            self.passed += 1
            
            modal = create_layout_customizer_modal()
            assert modal is not None
            print_pass("create_layout_customizer_modal() returns valid component")
            self.passed += 1
            
        except Exception as e:
            print_fail(f"Layout presets test failed: {e}")
            self.failed += 1
    
    def test_greeks_timeseries(self):
        """Test Greeks timeseries component."""
        try:
            from financial_dashboard.components.greeks_timeseries import (
                create_greeks_timeseries_panel,
                create_greeks_timeseries_figure,
                create_greeks_heatmap_figure,
            )
            
            panel = create_greeks_timeseries_panel()
            assert panel is not None
            print_pass("create_greeks_timeseries_panel() returns valid component")
            self.passed += 1
            
            fig = create_greeks_timeseries_figure()
            assert fig is not None
            print_pass("create_greeks_timeseries_figure() returns valid figure")
            self.passed += 1
            
            heatmap = create_greeks_heatmap_figure()
            assert heatmap is not None
            print_pass("create_greeks_heatmap_figure() returns valid figure")
            self.passed += 1
            
        except Exception as e:
            print_fail(f"Greeks timeseries test failed: {e}")
            self.failed += 1
    
    def test_accessibility(self):
        """Test accessibility component."""
        try:
            from financial_dashboard.components.accessibility import (
                create_accessibility_controls,
                create_skip_links,
                create_aria_live_region,
                create_responsive_container,
                create_mobile_nav,
            )
            
            controls = create_accessibility_controls()
            assert controls is not None
            print_pass("create_accessibility_controls() returns valid component")
            self.passed += 1
            
            skip = create_skip_links()
            assert skip is not None
            print_pass("create_skip_links() returns valid component")
            self.passed += 1
            
            aria = create_aria_live_region()
            assert aria is not None
            print_pass("create_aria_live_region() returns valid component")
            self.passed += 1
            
        except Exception as e:
            print_fail(f"Accessibility test failed: {e}")
            self.failed += 1
    
    def test_session_summary(self):
        """Test session summary component."""
        try:
            from financial_dashboard.components.session_summary import (
                create_session_summary_panel,
                create_connection_status_indicator,
                create_offline_mode_banner,
            )
            
            panel = create_session_summary_panel()
            assert panel is not None
            print_pass("create_session_summary_panel() returns valid component")
            self.passed += 1
            
            indicator = create_connection_status_indicator()
            assert indicator is not None
            print_pass("create_connection_status_indicator() returns valid component")
            self.passed += 1
            
            banner = create_offline_mode_banner()
            assert banner is not None
            print_pass("create_offline_mode_banner() returns valid component")
            self.passed += 1
            
        except Exception as e:
            print_fail(f"Session summary test failed: {e}")
            self.failed += 1
    
    def test_backtest_engine(self):
        """Test backtest engine."""
        try:
            from engines.backtesting.options_backtester import (
                VectorizedBacktester,
                BacktestConfig,
                StrategyType,
                quick_backtest,
            )
            
            # Test quick backtest
            result = quick_backtest(
                strategy=StrategyType.IRON_CONDOR,
                start_date="2023-06-01",
                end_date="2023-12-31",
            )
            
            assert result is not None
            print_pass("quick_backtest() executes successfully")
            self.passed += 1
            
            assert result.total_trades > 0
            print_pass(f"Backtest generated {result.total_trades} trades")
            self.passed += 1
            
            assert hasattr(result, 'sharpe_ratio')
            print_pass(f"Sharpe ratio calculated: {result.sharpe_ratio:.2f}")
            self.passed += 1
            
            assert hasattr(result, 'max_drawdown')
            print_pass(f"Max drawdown calculated: {result.max_drawdown:.2f}%")
            self.passed += 1
            
            assert hasattr(result, 'equity_curve')
            assert len(result.equity_curve) > 0
            print_pass("Equity curve generated")
            self.passed += 1
            
        except Exception as e:
            print_fail(f"Backtest engine test failed: {e}")
            self.failed += 1
    
    def test_monte_carlo(self):
        """Test Monte Carlo simulator."""
        try:
            from engines.backtesting.options_backtester import (
                MonteCarloSimulator,
                quick_backtest,
                StrategyType,
            )
            
            # Get trades from backtest
            result = quick_backtest(strategy=StrategyType.IRON_CONDOR)
            
            # Run Monte Carlo
            mc = MonteCarloSimulator(n_simulations=100)
            mc_results = mc.run_simulation(result.trades)
            
            assert mc_results is not None
            print_pass("Monte Carlo simulation runs successfully")
            self.passed += 1
            
            assert 'probability_profit' in mc_results
            print_pass(f"Probability of profit: {mc_results['probability_profit']:.1f}%")
            self.passed += 1
            
            assert 'median_final_equity' in mc_results
            print_pass(f"Median final equity: ${mc_results['median_final_equity']:,.0f}")
            self.passed += 1
            
        except Exception as e:
            print_fail(f"Monte Carlo test failed: {e}")
            self.failed += 1
    
    def test_walk_forward(self):
        """Test walk-forward optimizer."""
        try:
            from engines.backtesting.options_backtester import WalkForwardOptimizer
            
            wf = WalkForwardOptimizer(
                window_size=60,
                step_size=20,
            )
            
            assert wf is not None
            print_pass("WalkForwardOptimizer initializes successfully")
            self.passed += 1
            
            assert wf.window_size == 60
            print_pass("Walk-forward window size set correctly")
            self.passed += 1
            
        except Exception as e:
            print_fail(f"Walk-forward test failed: {e}")
            self.failed += 1
    
    def test_strategy_analysis(self):
        """Test strategy analysis component."""
        try:
            from financial_dashboard.components.strategy_analysis import (
                create_parameter_sensitivity_panel,
                create_strategy_comparison_panel,
                create_walk_forward_visualization,
                create_backtest_export_panel,
                create_sensitivity_heatmap,
                create_strategy_equity_comparison,
                create_strategy_radar,
            )
            
            sens_panel = create_parameter_sensitivity_panel()
            assert sens_panel is not None
            print_pass("create_parameter_sensitivity_panel() returns valid component")
            self.passed += 1
            
            comp_panel = create_strategy_comparison_panel()
            assert comp_panel is not None
            print_pass("create_strategy_comparison_panel() returns valid component")
            self.passed += 1
            
            wf_viz = create_walk_forward_visualization()
            assert wf_viz is not None
            print_pass("create_walk_forward_visualization() returns valid component")
            self.passed += 1
            
            export_panel = create_backtest_export_panel()
            assert export_panel is not None
            print_pass("create_backtest_export_panel() returns valid component")
            self.passed += 1
            
            # Test figures
            heatmap = create_sensitivity_heatmap()
            assert heatmap is not None
            print_pass("create_sensitivity_heatmap() returns valid figure")
            self.passed += 1
            
            equity = create_strategy_equity_comparison()
            assert equity is not None
            print_pass("create_strategy_equity_comparison() returns valid figure")
            self.passed += 1
            
            radar = create_strategy_radar()
            assert radar is not None
            print_pass("create_strategy_radar() returns valid figure")
            self.passed += 1
            
        except Exception as e:
            print_fail(f"Strategy analysis test failed: {e}")
            self.failed += 1
    
    def test_cli_tools(self):
        """Test CLI tools."""
        try:
            cli_path = self.project_root / "cli" / "alpaca_cli.py"
            
            # Check CLI exists
            assert cli_path.exists()
            print_pass("CLI script exists")
            self.passed += 1
            
            # Test help command
            result = subprocess.run(
                [sys.executable, str(cli_path), "--help"],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0
            assert "Available commands" in result.stdout or "usage" in result.stdout.lower()
            print_pass("CLI --help works")
            self.passed += 1
            
            # Test doctor command (non-destructive)
            result = subprocess.run(
                [sys.executable, str(cli_path), "doctor"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            # Doctor may return warnings but shouldn't crash
            assert "Python Version" in result.stdout or "DIAGNOSTICS" in result.stdout
            print_pass("CLI doctor command works")
            self.passed += 1
            
        except subprocess.TimeoutExpired:
            print_warn("CLI doctor command timed out")
            self.warnings += 1
        except Exception as e:
            print_fail(f"CLI tools test failed: {e}")
            self.failed += 1
    
    def test_server_health(self):
        """Test server health endpoint."""
        try:
            response = requests.get("http://localhost:8053/api/options/ready", timeout=5)
            
            if response.status_code == 200:
                print_pass("Server health endpoint returns 200")
                self.passed += 1
                
                data = response.json()
                if 'status' in data:
                    print_pass(f"Server status: {data.get('status')}")
                    self.passed += 1
            else:
                print_warn(f"Server returned status {response.status_code}")
                self.warnings += 1
                
        except requests.exceptions.ConnectionError:
            print_warn("Server not running - skipping health check")
            self.warnings += 1
        except Exception as e:
            print_fail(f"Server health test failed: {e}")
            self.failed += 1
    
    def test_component_imports(self):
        """Test all new component imports."""
        components = [
            ("trade_journal", "financial_dashboard.components.trade_journal"),
            ("keyboard_shortcuts", "financial_dashboard.components.keyboard_shortcuts"),
            ("export_utils", "financial_dashboard.components.export_utils"),
            ("layout_presets", "financial_dashboard.components.layout_presets"),
            ("greeks_timeseries", "financial_dashboard.components.greeks_timeseries"),
            ("accessibility", "financial_dashboard.components.accessibility"),
            ("session_summary", "financial_dashboard.components.session_summary"),
            ("strategy_analysis", "financial_dashboard.components.strategy_analysis"),
            ("backtest_dashboard", "financial_dashboard.components.backtest_dashboard"),
            ("options_backtester", "engines.backtesting.options_backtester"),
        ]
        
        for name, module_path in components:
            try:
                __import__(module_path)
                print_pass(f"Import {name}")
                self.passed += 1
            except ImportError as e:
                print_fail(f"Import {name}: {e}")
                self.failed += 1
    
    def print_summary(self):
        """Print test summary."""
        print_header("TEST SUMMARY")
        
        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0
        
        print(f"  {GREEN}Passed:{RESET}   {self.passed}")
        print(f"  {RED}Failed:{RESET}   {self.failed}")
        print(f"  {YELLOW}Warnings:{RESET} {self.warnings}")
        print(f"  {BLUE}Total:{RESET}    {total}")
        print(f"\n  Pass Rate: {pass_rate:.1f}%")
        
        if self.failed == 0:
            print(f"\n{GREEN}{BOLD}✓ ALL TESTS PASSED!{RESET}")
        else:
            print(f"\n{RED}{BOLD}✗ {self.failed} TEST(S) FAILED{RESET}")
        
        print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    """Run the test suite."""
    suite = EndToEndTestSuite()
    suite.run_all_tests()
    
    # Return exit code based on failures
    return 1 if suite.failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
