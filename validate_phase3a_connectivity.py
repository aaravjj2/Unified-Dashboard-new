#!/usr/bin/env python3
"""
Phase 3A: Azure Connectivity + CI/CD Prep Validation
====================================================

Validates Azure environment connectivity and CI/CD readiness for
the Unified Financial Dashboard deployment.

Tasks:
1. Environment Variable Validation
2. Azure Service Connectivity Tests
3. CI/CD Workflow Discovery
4. Pre-Deployment Docker Check
5. Playwright Integration Verification
6. Report Generation

Author: Agent 1B — Unified Financial Dashboard Team
Date: October 29, 2025
"""

import os
import sys
import json
import time
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import subprocess


@dataclass
class ConnectivityResult:
    """Result of a connectivity test"""
    service: str
    endpoint: str
    status: str  # "SUCCESS", "FAILURE", "MISSING"
    status_code: Optional[int]
    latency_ms: Optional[float]
    notes: str
    timestamp: str


@dataclass
class ValidationSummary:
    """Overall validation summary"""
    total_checks: int
    successful: int
    failed: int
    missing: int
    success_rate: float
    timestamp: str


class Phase3AValidator:
    """Azure Connectivity and CI/CD Validation"""
    
    def __init__(self, env_file: str = "keys.env"):
        self.env_file = Path(env_file)
        self.results: List[ConnectivityResult] = []
        self.env_vars: Dict[str, str] = {}
        self.required_azure_keys = [
            "AZURE_OPENAI_KEY",
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_STORAGE_KEY",
            "AZURE_STORAGE_ACCOUNT",
            "AZURE_WEBAPP_NAME",
            "AZURE_APPINSIGHTS_KEY",
        ]
        self.optional_azure_keys = [
            "AZURE_CLIENT_ID",
            "AZURE_CLIENT_SECRET",
            "AZURE_TENANT_ID",
            "AZURE_SUBSCRIPTION_ID",
            "AZURE_ML_WORKSPACE_NAME",
            "AZURE_ML_RESOURCE_GROUP",
            "AZURE_ML_ENDPOINT_URL",
            "AZURE_ML_API_KEY",
        ]
    
    def load_environment(self) -> Dict[str, str]:
        """Load environment variables from keys.env"""
        print("="*80)
        print("PHASE 3A: AZURE CONNECTIVITY + CI/CD PREP VALIDATION")
        print("="*80)
        print()
        print("Step 1: Loading Environment Variables")
        print("-" * 80)
        
        if not self.env_file.exists():
            print(f"❌ Error: {self.env_file} not found")
            return {}
        
        env_vars = {}
        with open(self.env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # Skip variable references for now
                    if not value.startswith('${'):
                        env_vars[key] = value
                        os.environ[key] = value
        
        self.env_vars = env_vars
        print(f"✅ Loaded {len(env_vars)} environment variables from {self.env_file}")
        print()
        
        return env_vars
    
    def validate_azure_keys(self) -> None:
        """Validate required and optional Azure keys"""
        print("Step 2: Azure Key Validation")
        print("-" * 80)
        
        # Check required keys
        print("Required Azure Keys:")
        missing_required = []
        for key in self.required_azure_keys:
            value = self.env_vars.get(key)
            if value:
                masked = value[:10] + "..." if len(value) > 10 else value
                print(f"  ✅ {key}: {masked}")
                
                # Add to results as environment check
                self.results.append(ConnectivityResult(
                    service=key,
                    endpoint="N/A (Environment Variable)",
                    status="SUCCESS",
                    status_code=None,
                    latency_ms=None,
                    notes="Key present in environment",
                    timestamp=datetime.now().isoformat()
                ))
            else:
                print(f"  ❌ {key}: MISSING")
                missing_required.append(key)
                
                self.results.append(ConnectivityResult(
                    service=key,
                    endpoint="N/A (Environment Variable)",
                    status="MISSING",
                    status_code=None,
                    latency_ms=None,
                    notes="Key not found in keys.env",
                    timestamp=datetime.now().isoformat()
                ))
        
        print()
        print("Optional Azure Keys:")
        for key in self.optional_azure_keys:
            value = self.env_vars.get(key)
            if value:
                masked = value[:10] + "..." if len(value) > 10 else value
                print(f"  ✅ {key}: {masked}")
                
                self.results.append(ConnectivityResult(
                    service=key,
                    endpoint="N/A (Environment Variable)",
                    status="SUCCESS",
                    status_code=None,
                    latency_ms=None,
                    notes="Optional key present",
                    timestamp=datetime.now().isoformat()
                ))
            else:
                print(f"  ⚠️  {key}: NOT SET")
        
        print()
        if missing_required:
            print(f"⚠️  WARNING: {len(missing_required)} required Azure keys missing:")
            for key in missing_required:
                print(f"     - {key}")
            print()
            print("ℹ️  Note: Some keys may need to be added to keys.env for full Azure deployment")
        else:
            print("✅ All required Azure keys present")
        
        print()
    
    def test_azure_ml_endpoint(self) -> None:
        """Test Azure ML endpoint connectivity"""
        print("Step 3: Azure ML Endpoint Connectivity")
        print("-" * 80)
        
        endpoint_url = self.env_vars.get("AZURE_ML_ENDPOINT_URL")
        api_key = self.env_vars.get("AZURE_ML_API_KEY")
        
        if not endpoint_url:
            print("⚠️  AZURE_ML_ENDPOINT_URL not configured, skipping ML endpoint test")
            self.results.append(ConnectivityResult(
                service="Azure ML Inference",
                endpoint="N/A",
                status="MISSING",
                status_code=None,
                latency_ms=None,
                notes="Endpoint URL not configured",
                timestamp=datetime.now().isoformat()
            ))
            print()
            return
        
        print(f"Testing: {endpoint_url}")
        
        # Test with a lightweight health check (HEAD request)
        try:
            start = time.time()
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            # Try HEAD first for lightweight check
            response = requests.head(endpoint_url, headers=headers, timeout=10)
            latency_ms = (time.time() - start) * 1000
            
            if response.status_code in [200, 405]:  # 405 = Method Not Allowed (HEAD not supported, but endpoint exists)
                status = "SUCCESS"
                notes = "Endpoint reachable"
                print(f"  ✅ Status: {response.status_code} | Latency: {latency_ms:.0f}ms")
            elif response.status_code == 401:
                status = "FAILURE"
                notes = "Authentication failed - check API key"
                print(f"  ❌ Status: {response.status_code} (Unauthorized) | Latency: {latency_ms:.0f}ms")
            else:
                status = "FAILURE"
                notes = f"Unexpected status code: {response.status_code}"
                print(f"  ⚠️  Status: {response.status_code} | Latency: {latency_ms:.0f}ms")
            
            self.results.append(ConnectivityResult(
                service="Azure ML Inference",
                endpoint=endpoint_url,
                status=status,
                status_code=response.status_code,
                latency_ms=latency_ms,
                notes=notes,
                timestamp=datetime.now().isoformat()
            ))
        
        except requests.exceptions.Timeout:
            print(f"  ❌ Timeout after 10 seconds")
            self.results.append(ConnectivityResult(
                service="Azure ML Inference",
                endpoint=endpoint_url,
                status="FAILURE",
                status_code=None,
                latency_ms=None,
                notes="Request timeout (>10s)",
                timestamp=datetime.now().isoformat()
            ))
        
        except requests.exceptions.ConnectionError as e:
            print(f"  ❌ Connection failed: {str(e)[:100]}")
            self.results.append(ConnectivityResult(
                service="Azure ML Inference",
                endpoint=endpoint_url,
                status="FAILURE",
                status_code=None,
                latency_ms=None,
                notes=f"Connection error: {str(e)[:100]}",
                timestamp=datetime.now().isoformat()
            ))
        
        except Exception as e:
            print(f"  ❌ Error: {str(e)[:100]}")
            self.results.append(ConnectivityResult(
                service="Azure ML Inference",
                endpoint=endpoint_url,
                status="FAILURE",
                status_code=None,
                latency_ms=None,
                notes=f"Error: {str(e)[:100]}",
                timestamp=datetime.now().isoformat()
            ))
        
        print()
    
    def test_azure_openai_endpoint(self) -> None:
        """Test Azure OpenAI endpoint connectivity"""
        print("Step 4: Azure OpenAI Endpoint Connectivity")
        print("-" * 80)
        
        endpoint = self.env_vars.get("AZURE_OPENAI_ENDPOINT")
        api_key = self.env_vars.get("AZURE_OPENAI_KEY")
        
        if not endpoint:
            print("⚠️  AZURE_OPENAI_ENDPOINT not configured")
            self.results.append(ConnectivityResult(
                service="Azure OpenAI",
                endpoint="N/A",
                status="MISSING",
                status_code=None,
                latency_ms=None,
                notes="Endpoint not configured in keys.env",
                timestamp=datetime.now().isoformat()
            ))
            print()
            return
        
        print(f"Testing: {endpoint}")
        
        # Test connectivity with a simple HEAD request
        try:
            start = time.time()
            headers = {}
            if api_key:
                headers["api-key"] = api_key
            
            response = requests.head(endpoint, headers=headers, timeout=10)
            latency_ms = (time.time() - start) * 1000
            
            if response.status_code in [200, 405]:
                status = "SUCCESS"
                notes = "Endpoint reachable"
                print(f"  ✅ Status: {response.status_code} | Latency: {latency_ms:.0f}ms")
            elif response.status_code == 401:
                status = "FAILURE"
                notes = "Authentication failed"
                print(f"  ❌ Status: {response.status_code} (Unauthorized) | Latency: {latency_ms:.0f}ms")
            else:
                status = "FAILURE"
                notes = f"Status code: {response.status_code}"
                print(f"  ⚠️  Status: {response.status_code} | Latency: {latency_ms:.0f}ms")
            
            self.results.append(ConnectivityResult(
                service="Azure OpenAI",
                endpoint=endpoint,
                status=status,
                status_code=response.status_code,
                latency_ms=latency_ms,
                notes=notes,
                timestamp=datetime.now().isoformat()
            ))
        
        except Exception as e:
            print(f"  ❌ Error: {str(e)[:100]}")
            self.results.append(ConnectivityResult(
                service="Azure OpenAI",
                endpoint=endpoint,
                status="FAILURE",
                status_code=None,
                latency_ms=None,
                notes=f"Error: {str(e)[:100]}",
                timestamp=datetime.now().isoformat()
            ))
        
        print()
    
    def discover_ci_cd_workflows(self) -> Dict[str, Any]:
        """Discover and analyze CI/CD workflows"""
        print("Step 5: CI/CD Workflow Discovery")
        print("-" * 80)
        
        workflows_dir = Path(".github/workflows")
        ci_file = workflows_dir / "ci.yml"
        cd_file = workflows_dir / "cd.yml"
        
        workflow_info = {
            "workflows_dir_exists": workflows_dir.exists(),
            "ci_yml_exists": ci_file.exists(),
            "cd_yml_exists": cd_file.exists(),
            "workflows_found": [],
            "playwright_jobs": [],
            "pytest_jobs": [],
            "docker_build_steps": [],
            "acr_deployment_steps": [],
            "webapp_deployment_steps": [],
            "secrets_referenced": [],
        }
        
        if not workflows_dir.exists():
            print(f"⚠️  Workflows directory not found: {workflows_dir}")
            print("ℹ️  CI/CD workflows need to be created for automated deployment")
            print()
            return workflow_info
        
        print(f"Workflows directory: {workflows_dir}")
        
        # List all workflow files
        workflow_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))
        print(f"Found {len(workflow_files)} workflow file(s):")
        for wf in workflow_files:
            print(f"  - {wf.name}")
            workflow_info["workflows_found"].append(str(wf.name))
        
        print()
        
        # Analyze CI workflow
        if ci_file.exists():
            print(f"Analyzing: {ci_file.name}")
            with open(ci_file) as f:
                content = f.read()
                
                # Check for test frameworks
                if "playwright" in content.lower():
                    print("  ✅ Playwright tests found")
                    workflow_info["playwright_jobs"].append("CI workflow contains Playwright")
                else:
                    print("  ⚠️  Playwright tests not found")
                
                if "pytest" in content.lower():
                    print("  ✅ pytest jobs found")
                    workflow_info["pytest_jobs"].append("CI workflow contains pytest")
                else:
                    print("  ⚠️  pytest jobs not found")
                
                # Check for Docker
                if "docker build" in content.lower() or "docker-compose" in content.lower():
                    print("  ✅ Docker build steps found")
                    workflow_info["docker_build_steps"].append("CI workflow contains Docker build")
                else:
                    print("  ⚠️  Docker build steps not found")
                
                print()
        else:
            print(f"⚠️  CI workflow not found: {ci_file}")
            print()
        
        # Analyze CD workflow
        if cd_file.exists():
            print(f"Analyzing: {cd_file.name}")
            with open(cd_file) as f:
                content = f.read()
                
                # Check for deployment steps
                if "acr" in content.lower() or "azure container registry" in content.lower():
                    print("  ✅ ACR deployment steps found")
                    workflow_info["acr_deployment_steps"].append("CD workflow pushes to ACR")
                else:
                    print("  ⚠️  ACR deployment not found")
                
                if "webapp" in content.lower() or "app service" in content.lower():
                    print("  ✅ WebApp deployment steps found")
                    workflow_info["webapp_deployment_steps"].append("CD workflow deploys to App Service")
                else:
                    print("  ⚠️  WebApp deployment not found")
                
                # Check for secrets
                if "secrets." in content:
                    print("  ✅ Secrets injection found")
                    workflow_info["secrets_referenced"].append("CD workflow uses GitHub secrets")
                else:
                    print("  ⚠️  No secrets injection found")
                
                print()
        else:
            print(f"⚠️  CD workflow not found: {cd_file}")
            print()
        
        return workflow_info
    
    def check_playwright_integration(self) -> Dict[str, Any]:
        """Check for Playwright test integration"""
        print("Step 6: Playwright Integration Verification")
        print("-" * 80)
        
        # Look for phase9c Playwright validators
        playwright_files = [
            "phase9c1_chromium_forced_validator.py",
            "tests/ui/phase9c1_chromium_forced_validator.py",
            "financial_dashboard/playwright_test.py",
            "tests/e2e/test_main_workflows.py",
        ]
        
        found_files = []
        for file_path in playwright_files:
            path = Path(file_path)
            if path.exists():
                print(f"  ✅ Found: {file_path}")
                found_files.append(str(file_path))
            else:
                print(f"  ⚠️  Not found: {file_path}")
        
        print()
        
        playwright_info = {
            "playwright_files_found": found_files,
            "ci_integration": False,
            "recommendation": ""
        }
        
        # Check CI integration
        ci_file = Path(".github/workflows/ci.yml")
        if ci_file.exists():
            with open(ci_file) as f:
                content = f.read()
                for pf in found_files:
                    if pf in content:
                        print(f"  ✅ {pf} referenced in CI workflow")
                        playwright_info["ci_integration"] = True
                        break
        
        if not playwright_info["ci_integration"] and found_files:
            recommendation = f"Add validation step to CI workflow: python {found_files[0]} --env=staging"
            print(f"  ⚠️  Recommendation: {recommendation}")
            playwright_info["recommendation"] = recommendation
        
        print()
        
        return playwright_info
    
    def generate_reports(self, workflow_info: Dict, playwright_info: Dict) -> None:
        """Generate validation reports"""
        print("Step 7: Generating Reports")
        print("-" * 80)
        
        # Calculate summary
        total = len(self.results)
        successful = sum(1 for r in self.results if r.status == "SUCCESS")
        failed = sum(1 for r in self.results if r.status == "FAILURE")
        missing = sum(1 for r in self.results if r.status == "MISSING")
        success_rate = (successful / total * 100) if total > 0 else 0
        
        summary = ValidationSummary(
            total_checks=total,
            successful=successful,
            failed=failed,
            missing=missing,
            success_rate=success_rate,
            timestamp=datetime.now().isoformat()
        )
        
        # Generate JSON report
        json_report = {
            "summary": asdict(summary),
            "connectivity_results": [asdict(r) for r in self.results],
            "ci_cd_workflow_info": workflow_info,
            "playwright_integration": playwright_info,
        }
        
        json_path = Path("ci_cd_predeploy_results.json")
        with open(json_path, 'w') as f:
            json.dump(json_report, f, indent=2)
        
        print(f"✅ JSON report saved: {json_path}")
        
        # Generate Markdown report
        self._generate_markdown_report(summary, workflow_info, playwright_info)
        
        print()
    
    def _generate_markdown_report(self, summary: ValidationSummary, workflow_info: Dict, playwright_info: Dict) -> None:
        """Generate detailed markdown report"""
        
        md_content = f"""# Phase 3A: Azure Connectivity + CI/CD Prep Validation Report

**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**Author:** Agent 1B — Unified Financial Dashboard Team  
**Mission:** Phase 3A Azure Environment Validation

---

## 🎯 Executive Summary

| Metric | Value |
|--------|-------|
| Total Checks | {summary.total_checks} |
| Successful | {summary.successful} ✅ |
| Failed | {summary.failed} ❌ |
| Missing | {summary.missing} ⚠️ |
| Success Rate | {summary.success_rate:.1f}% |

---

## 📊 Connectivity Test Results

| Service | Endpoint | Status | Status Code | Latency (ms) | Notes |
|---------|----------|--------|-------------|--------------|-------|
"""
        
        for result in self.results:
            status_icon = {"SUCCESS": "✅", "FAILURE": "❌", "MISSING": "⚠️"}.get(result.status, "❓")
            endpoint_short = result.endpoint[:50] + "..." if len(result.endpoint) > 50 else result.endpoint
            status_code_str = str(result.status_code) if result.status_code else "N/A"
            latency_str = f"{result.latency_ms:.0f}" if result.latency_ms is not None else "N/A"
            
            md_content += f"| {result.service} | {endpoint_short} | {status_icon} {result.status} | {status_code_str} | {latency_str} | {result.notes} |\n"
        
        md_content += f"""
---

## 🔧 CI/CD Workflow Analysis

### Workflow Files

- Workflows Directory: **{'✅ Exists' if workflow_info['workflows_dir_exists'] else '❌ Missing'}**
- CI Workflow (ci.yml): **{'✅ Found' if workflow_info['ci_yml_exists'] else '❌ Missing'}**
- CD Workflow (cd.yml): **{'✅ Found' if workflow_info['cd_yml_exists'] else '❌ Missing'}**

### Discovered Workflows

{chr(10).join(f'- {wf}' for wf in workflow_info['workflows_found']) if workflow_info['workflows_found'] else '⚠️ No workflows found'}

### Test Framework Integration

- **Playwright Tests:** {'✅ ' + ', '.join(workflow_info['playwright_jobs']) if workflow_info['playwright_jobs'] else '⚠️ Not found in workflows'}
- **pytest Tests:** {'✅ ' + ', '.join(workflow_info['pytest_jobs']) if workflow_info['pytest_jobs'] else '⚠️ Not found in workflows'}

### Deployment Pipeline

- **Docker Build:** {'✅ ' + ', '.join(workflow_info['docker_build_steps']) if workflow_info['docker_build_steps'] else '⚠️ Not configured'}
- **ACR Deployment:** {'✅ ' + ', '.join(workflow_info['acr_deployment_steps']) if workflow_info['acr_deployment_steps'] else '⚠️ Not configured'}
- **WebApp Deployment:** {'✅ ' + ', '.join(workflow_info['webapp_deployment_steps']) if workflow_info['webapp_deployment_steps'] else '⚠️ Not configured'}
- **Secrets Injection:** {'✅ ' + ', '.join(workflow_info['secrets_referenced']) if workflow_info['secrets_referenced'] else '⚠️ Not configured'}

---

## 🧪 Playwright Integration Status

### Test Files Found

{chr(10).join(f'- ✅ {pf}' for pf in playwright_info['playwright_files_found']) if playwright_info['playwright_files_found'] else '⚠️ No Playwright test files found'}

### CI Integration

- **Status:** {'✅ Integrated in CI workflow' if playwright_info['ci_integration'] else '⚠️ Not integrated in CI'}
- **Recommendation:** {playwright_info['recommendation'] if playwright_info['recommendation'] else 'N/A'}

---

## 🚨 Issues Identified

### Missing Azure Keys

The following required Azure keys are missing from `keys.env`:

"""
        
        missing_keys = [r.service for r in self.results if r.status == "MISSING" and r.service.startswith("AZURE_")]
        if missing_keys:
            for key in missing_keys:
                md_content += f"- ❌ `{key}`\n"
        else:
            md_content += "✅ All required Azure keys present\n"
        
        md_content += """
### Failed Connectivity Tests

"""
        
        failed_tests = [r for r in self.results if r.status == "FAILURE"]
        if failed_tests:
            for test in failed_tests:
                md_content += f"- ❌ **{test.service}**: {test.notes}\n"
        else:
            md_content += "✅ No failed connectivity tests\n"
        
        md_content += f"""
---

## 📋 Recommendations

### Immediate Actions Required

"""
        
        recommendations = []
        
        if missing_keys:
            recommendations.append("1. **Add Missing Azure Keys**: Update `keys.env` with required Azure credentials")
        
        if not workflow_info['ci_yml_exists']:
            recommendations.append("2. **Create CI Workflow**: Add `.github/workflows/ci.yml` for automated testing")
        
        if not workflow_info['cd_yml_exists']:
            recommendations.append("3. **Create CD Workflow**: Add `.github/workflows/cd.yml` for automated deployment")
        
        if not playwright_info['ci_integration'] and playwright_info['playwright_files_found']:
            recommendations.append(f"4. **Integrate Playwright**: {playwright_info['recommendation']}")
        
        if not workflow_info['docker_build_steps']:
            recommendations.append("5. **Add Docker Build**: Configure Docker build steps in CI workflow")
        
        if recommendations:
            md_content += "\n".join(recommendations) + "\n"
        else:
            md_content += "✅ No critical recommendations - system ready for deployment\n"
        
        md_content += """
### Next Steps

"""
        
        if summary.success_rate >= 80 and not missing_keys:
            md_content += """
✅ **PROCEED TO PHASE 3B**: Auto Deployment & Staging Validation

The system has passed validation with acceptable success rate. Proceed with:
- Docker image build
- Azure Container Registry push
- App Service deployment
- Staging environment validation
"""
        else:
            md_content += f"""
⚠️ **HALT**: Address critical issues before proceeding

Current success rate: {summary.success_rate:.1f}%

Please resolve the following before proceeding to Phase 3B:
1. Add missing Azure keys to `keys.env`
2. Fix failed connectivity tests
3. Set up CI/CD workflows
4. Verify Playwright integration
"""
        
        md_content += """
---

## 📚 References

- **JSON Report**: `ci_cd_predeploy_results.json`
- **Environment File**: `keys.env`
- **Workflows Directory**: `.github/workflows/`
- **Playwright Tests**: See Playwright Integration Status section

---

**Report Generated:** """ + datetime.now().isoformat() + """  
**Validation Script:** `validate_phase3a_connectivity.py`  
**Mission Status:** """ + ("✅ READY FOR PHASE 3B" if summary.success_rate >= 80 and not missing_keys else "⚠️ BLOCKED - RESOLVE ISSUES")

        
        md_path = Path("PHASE3A_CONNECTIVITY_REPORT.md")
        with open(md_path, 'w') as f:
            f.write(md_content)
        
        print(f"✅ Markdown report saved: {md_path}")
    
    def run_validation(self) -> int:
        """Run complete validation suite"""
        # Step 1: Load environment
        self.load_environment()
        
        # Step 2: Validate Azure keys
        self.validate_azure_keys()
        
        # Step 3: Test Azure ML endpoint
        self.test_azure_ml_endpoint()
        
        # Step 4: Test Azure OpenAI endpoint
        self.test_azure_openai_endpoint()
        
        # Step 5: Discover CI/CD workflows
        workflow_info = self.discover_ci_cd_workflows()
        
        # Step 6: Check Playwright integration
        playwright_info = self.check_playwright_integration()
        
        # Step 7: Generate reports
        self.generate_reports(workflow_info, playwright_info)
        
        # Summary
        print("="*80)
        print("VALIDATION COMPLETE")
        print("="*80)
        
        successful = sum(1 for r in self.results if r.status == "SUCCESS")
        total = len(self.results)
        success_rate = (successful / total * 100) if total > 0 else 0
        
        print(f"Total Checks: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {sum(1 for r in self.results if r.status == 'FAILURE')}")
        print(f"Missing: {sum(1 for r in self.results if r.status == 'MISSING')}")
        print(f"Success Rate: {success_rate:.1f}%")
        print()
        
        missing_required = [r.service for r in self.results if r.status == "MISSING" and r.service in self.required_azure_keys]
        
        if success_rate >= 80 and not missing_required:
            print("✅ VALIDATION PASSED - READY FOR PHASE 3B")
            return 0
        else:
            print("⚠️ VALIDATION INCOMPLETE - RESOLVE ISSUES BEFORE PHASE 3B")
            return 1


if __name__ == "__main__":
    validator = Phase3AValidator()
    exit_code = validator.run_validation()
    sys.exit(exit_code)
