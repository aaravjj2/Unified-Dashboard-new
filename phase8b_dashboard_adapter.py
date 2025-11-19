#!/usr/bin/env python3
"""
Phase 8B Dashboard Adapter - Schema Validation & Integration
Ensures Phase 7/8 simulation outputs align with dashboard requirements
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))


class Phase8BDashboardAdapter:
    """
    Validates schema alignment between Phase 8 outputs and dashboard requirements
    """
    
    def __init__(self, output_dir: str = "outputs/phase8b_dashboard"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.validation_results = []
    
    def validate_batch_simulation_schema(
        self,
        batch_result_path: Path
    ) -> Dict[str, Any]:
        """
        Validate BatchSimulationResult schema alignment
        
        Args:
            batch_result_path: Path to batch simulation JSON
        
        Returns:
            Validation result
        """
        print(f"\n{'='*80}")
        print(f"VALIDATING: Batch Simulation Schema")
        print(f"{'='*80}")
        print(f"File: {batch_result_path}")
        print()
        
        if not batch_result_path.exists():
            print(f"❌ File not found")
            return {"status": "file_not_found"}
        
        # Load batch result
        with open(batch_result_path, 'r') as f:
            batch_data = json.load(f)
        
        # Expected schema for dashboard
        required_fields = {
            "batch_id": str,
            "timestamp": str,
            "portfolio_results": list,
            "aggregate_metrics": dict,
            "total_execution_time_ms": (int, float),
            "scenarios_per_second": (int, float),
            "cache_hit_rate": (int, float)
        }
        
        required_aggregate_fields = {
            "mean_return": (int, float),
            "median_return": (int, float),
            "mean_sharpe": (int, float),
            "mean_var_95": (int, float),
            "worst_drawdown": (int, float)
        }
        
        required_portfolio_fields = {
            "scenario_id": str,
            "total_return": (int, float),
            "sharpe_ratio": (int, float),
            "max_drawdown": (int, float),
            "volatility": (int, float)
        }
        
        # Validate top-level fields
        missing_fields = []
        type_mismatches = []
        
        for field, expected_type in required_fields.items():
            if field not in batch_data:
                missing_fields.append(field)
            else:
                if not isinstance(batch_data[field], expected_type):
                    type_mismatches.append({
                        "field": field,
                        "expected": str(expected_type),
                        "actual": type(batch_data[field]).__name__
                    })
        
        # Validate aggregate metrics
        if "aggregate_metrics" in batch_data:
            for field, expected_type in required_aggregate_fields.items():
                if field not in batch_data["aggregate_metrics"]:
                    missing_fields.append(f"aggregate_metrics.{field}")
                else:
                    if not isinstance(batch_data["aggregate_metrics"][field], expected_type):
                        type_mismatches.append({
                            "field": f"aggregate_metrics.{field}",
                            "expected": str(expected_type),
                            "actual": type(batch_data["aggregate_metrics"][field]).__name__
                        })
        
        # Validate portfolio results (sample first entry)
        if "portfolio_results" in batch_data and len(batch_data["portfolio_results"]) > 0:
            sample_result = batch_data["portfolio_results"][0]
            for field, expected_type in required_portfolio_fields.items():
                if field not in sample_result:
                    missing_fields.append(f"portfolio_results[].{field}")
                else:
                    if not isinstance(sample_result[field], expected_type):
                        type_mismatches.append({
                            "field": f"portfolio_results[].{field}",
                            "expected": str(expected_type),
                            "actual": type(sample_result[field]).__name__
                        })
        
        # Validation result
        is_valid = len(missing_fields) == 0 and len(type_mismatches) == 0
        
        validation = {
            "file": str(batch_result_path),
            "is_valid": is_valid,
            "missing_fields": missing_fields,
            "type_mismatches": type_mismatches,
            "num_portfolio_results": len(batch_data.get("portfolio_results", [])),
            "timestamp": datetime.now().isoformat()
        }
        
        # Display results
        if is_valid:
            print(f"✅ Schema validation PASSED")
            print(f"   All required fields present with correct types")
            print(f"   Portfolio results: {validation['num_portfolio_results']}")
        else:
            print(f"❌ Schema validation FAILED")
            if missing_fields:
                print(f"   Missing fields: {', '.join(missing_fields)}")
            if type_mismatches:
                print(f"   Type mismatches:")
                for mismatch in type_mismatches:
                    print(f"     {mismatch['field']}: expected {mismatch['expected']}, got {mismatch['actual']}")
        
        print(f"{'='*80}\n")
        
        self.validation_results.append(validation)
        return validation
    
    def validate_chart_js_compatibility(
        self,
        batch_result_path: Path
    ) -> Dict[str, Any]:
        """
        Validate Chart.js data structure compatibility
        
        Args:
            batch_result_path: Path to batch simulation JSON
        
        Returns:
            Chart.js validation result
        """
        print(f"\n{'='*80}")
        print(f"VALIDATING: Chart.js Compatibility")
        print(f"{'='*80}")
        print(f"File: {batch_result_path}")
        print()
        
        if not batch_result_path.exists():
            print(f"❌ File not found")
            return {"status": "file_not_found"}
        
        # Load batch result
        with open(batch_result_path, 'r') as f:
            batch_data = json.load(f)
        
        # Extract data for Chart.js
        portfolio_results = batch_data.get("portfolio_results", [])
        
        # Create Chart.js compatible data structure
        chart_data = {
            "labels": [],
            "datasets": [
                {
                    "label": "Total Return (%)",
                    "data": [],
                    "backgroundColor": "rgba(54, 162, 235, 0.5)"
                },
                {
                    "label": "Sharpe Ratio",
                    "data": [],
                    "backgroundColor": "rgba(255, 99, 132, 0.5)"
                }
            ]
        }
        
        for result in portfolio_results:
            chart_data["labels"].append(result.get("scenario_id", "Unknown"))
            chart_data["datasets"][0]["data"].append(result.get("total_return", 0) * 100)
            chart_data["datasets"][1]["data"].append(result.get("sharpe_ratio", 0))
        
        # Validate structure
        is_valid = (
            len(chart_data["labels"]) > 0 and
            len(chart_data["datasets"]) > 0 and
            len(chart_data["datasets"][0]["data"]) == len(chart_data["labels"])
        )
        
        validation = {
            "file": str(batch_result_path),
            "is_valid": is_valid,
            "num_data_points": len(chart_data["labels"]),
            "num_datasets": len(chart_data["datasets"]),
            "chart_data_sample": {
                "labels": chart_data["labels"][:3],
                "total_returns": chart_data["datasets"][0]["data"][:3],
                "sharpe_ratios": chart_data["datasets"][1]["data"][:3]
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # Display results
        if is_valid:
            print(f"✅ Chart.js compatibility PASSED")
            print(f"   Data points: {validation['num_data_points']}")
            print(f"   Datasets: {validation['num_datasets']}")
        else:
            print(f"❌ Chart.js compatibility FAILED")
        
        print(f"{'='*80}\n")
        
        # Save Chart.js data sample
        chart_data_path = self.output_dir / "chartjs_data_sample.json"
        with open(chart_data_path, 'w') as f:
            json.dump(chart_data, f, indent=2)
        
        print(f"💾 Chart.js data saved: {chart_data_path}\n")
        
        return validation
    
    def validate_phase6_integration(self) -> Dict[str, Any]:
        """
        Validate integration with Phase 6 Azure ML outputs
        
        Returns:
            Integration validation result
        """
        print(f"\n{'='*80}")
        print(f"VALIDATING: Phase 6 Azure ML Integration")
        print(f"{'='*80}")
        print()
        
        # Check if Phase 6 module exists
        phase6_path = Path("financial_dashboard/tabs/azure_ml_lab/phase6_azure_integration")
        
        if not phase6_path.exists():
            print(f"⚠️ Phase 6 directory not found: {phase6_path}")
            return {"status": "phase6_not_found"}
        
        # Check for key Phase 6 outputs
        phase6_checks = {
            "__init__.py": phase6_path / "__init__.py",
            "explainability_azure.py": phase6_path / "explainability_azure.py",
            "options_forecast_azure.py": phase6_path / "options_forecast_azure.py",
            "phase6_cache_config.py": phase6_path / "phase6_cache_config.py"
        }
        
        existing_files = []
        missing_files = []
        
        for name, file_path in phase6_checks.items():
            if file_path.exists():
                existing_files.append(name)
                print(f"✅ Found: {name}")
            else:
                missing_files.append(name)
                print(f"❌ Missing: {name}")
        
        # Check for cache integration
        cache_integration_ready = "phase6_cache_config.py" in existing_files
        
        validation = {
            "phase6_directory": str(phase6_path),
            "existing_files": existing_files,
            "missing_files": missing_files,
            "cache_integration_ready": cache_integration_ready,
            "integration_status": "ready" if len(missing_files) == 0 else "partial",
            "timestamp": datetime.now().isoformat()
        }
        
        print()
        if len(missing_files) == 0:
            print(f"✅ Phase 6 integration READY")
        else:
            print(f"⚠️ Phase 6 integration PARTIAL ({len(missing_files)} files missing)")
        
        print(f"{'='*80}\n")
        
        return validation
    
    def generate_integration_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive integration report
        
        Returns:
            Integration report
        """
        print(f"\n{'='*80}")
        print(f"INTEGRATION REPORT")
        print(f"{'='*80}")
        print()
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "validation_results": self.validation_results,
            "summary": {
                "total_validations": len(self.validation_results),
                "passed": sum(1 for v in self.validation_results if v.get("is_valid", False)),
                "failed": sum(1 for v in self.validation_results if not v.get("is_valid", False))
            }
        }
        
        # Save report
        report_path = self.output_dir / "dashboard_schema_validation.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"💾 Integration report saved: {report_path}")
        
        # Generate markdown report
        self._generate_markdown_report(report)
        
        return report
    
    def _generate_markdown_report(self, report: Dict[str, Any]):
        """Generate markdown integration report"""
        md_path = self.output_dir / "integration_alignment_report.md"
        
        with open(md_path, 'w') as f:
            f.write("# Phase 8B Dashboard Integration Report\n\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Summary\n\n")
            f.write(f"- **Total Validations:** {report['summary']['total_validations']}\n")
            f.write(f"- **Passed:** {report['summary']['passed']}\n")
            f.write(f"- **Failed:** {report['summary']['failed']}\n\n")
            
            f.write("## Validation Results\n\n")
            for validation in report['validation_results']:
                status = "✅ PASS" if validation.get("is_valid", False) else "❌ FAIL"
                f.write(f"### {validation.get('file', 'Unknown')} {status}\n\n")
                
                if "missing_fields" in validation and validation["missing_fields"]:
                    f.write("**Missing Fields:**\n")
                    for field in validation["missing_fields"]:
                        f.write(f"- `{field}`\n")
                    f.write("\n")
                
                if "type_mismatches" in validation and validation["type_mismatches"]:
                    f.write("**Type Mismatches:**\n")
                    for mismatch in validation["type_mismatches"]:
                        f.write(f"- `{mismatch['field']}`: expected `{mismatch['expected']}`, got `{mismatch['actual']}`\n")
                    f.write("\n")
        
        print(f"💾 Markdown report saved: {md_path}")


def main():
    """Run Phase 8B dashboard adapter validation"""
    print("=" * 80)
    print("PHASE 8B: DASHBOARD INTEGRATION VALIDATION")
    print("=" * 80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    adapter = Phase8BDashboardAdapter()
    
    # Find latest batch result
    batch_dir = Path("outputs/phase7_batch")
    if batch_dir.exists():
        batch_results = list(batch_dir.glob("**/batch_*_results.json"))
        if batch_results:
            latest_batch = sorted(batch_results)[-1]
            print(f"Using latest batch result: {latest_batch}\n")
            
            # Validate schema
            adapter.validate_batch_simulation_schema(latest_batch)
            
            # Validate Chart.js compatibility
            adapter.validate_chart_js_compatibility(latest_batch)
        else:
            print("⚠️ No batch results found\n")
    else:
        print("⚠️ Batch output directory not found\n")
    
    # Validate Phase 6 integration
    adapter.validate_phase6_integration()
    
    # Generate report
    adapter.generate_integration_report()
    
    print("\n" + "=" * 80)
    print("✅ PHASE 8B DASHBOARD VALIDATION COMPLETE")
    print("=" * 80)
    print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


if __name__ == "__main__":
    main()
