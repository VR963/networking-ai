#!/usr/bin/env python3
"""
Comprehensive Test Runner

Runs all test suites and generates a master report including:
- Registration flow tests
- Agent interaction tests
- System health analysis
- Master AI coordination report
"""

import subprocess
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


class ComprehensiveTestRunner:
    """Run all test suites and generate master report."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = {}
        self.start_time = datetime.now()

    def run_command(self, cmd: list, description: str) -> Dict[str, Any]:
        """Run a command and capture results."""
        print(f"\n{'='*80}")
        print(f"Running: {description}")
        print(f"{'='*80}")

        start = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes max
            )
            duration = time.time() - start

            return {
                "success": result.returncode == 0,
                "duration": duration,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            duration = time.time() - start
            return {
                "success": False,
                "duration": duration,
                "error": "Test timed out after 5 minutes",
                "returncode": -1
            }
        except Exception as e:
            duration = time.time() - start
            return {
                "success": False,
                "duration": duration,
                "error": str(e),
                "returncode": -1
            }

    def run_registration_tests(self) -> Dict[str, Any]:
        """Run registration flow tests."""
        result = self.run_command(
            [
                sys.executable,
                "test_registration_flow.py",
                "--url", self.base_url,
                "--output", "registration_test_report.json"
            ],
            "Registration Flow Tests"
        )

        # Load the generated report
        report_file = Path("registration_test_report.json")
        if report_file.exists():
            with open(report_file) as f:
                result["detailed_report"] = json.load(f)

        return result

    def run_agent_interaction_tests(self) -> Dict[str, Any]:
        """Run agent interaction tests."""
        result = self.run_command(
            [
                sys.executable,
                "test_agent_interactions.py",
                "--url", self.base_url,
                "--output", "agent_interaction_test_report.json"
            ],
            "Agent Interaction Tests"
        )

        # Load the generated report
        report_file = Path("agent_interaction_test_report.json")
        if report_file.exists():
            with open(report_file) as f:
                result["detailed_report"] = json.load(f)

        return result

    def analyze_master_ai_performance(self) -> Dict[str, Any]:
        """Analyze Master AI performance from test results."""
        analysis = {
            "coordination_effectiveness": "Not tested",
            "agent_orchestration": "Not tested",
            "knowledge_distribution": "Not tested",
            "matching_accuracy": "Not tested",
            "recommendations": []
        }

        # Check if agent tests ran
        if "agent_interactions" in self.results:
            agent_results = self.results["agent_interactions"]
            if agent_results.get("success") and "detailed_report" in agent_results:
                report = agent_results["detailed_report"]
                capabilities = report.get("capabilities_verified", {})

                # Analyze coordination
                if capabilities.get("master_ai_matching"):
                    analysis["coordination_effectiveness"] = "Working"
                    analysis["matching_accuracy"] = "Verified"

                if capabilities.get("multi_agent_collaboration"):
                    analysis["agent_orchestration"] = "Working"

                if capabilities.get("knowledge_sharing"):
                    analysis["knowledge_distribution"] = "Working"

                # Generate recommendations
                if not capabilities.get("agent_messaging"):
                    analysis["recommendations"].append(
                        "Implement direct agent-to-agent messaging for improved communication"
                    )

                if not capabilities.get("knowledge_sharing"):
                    analysis["recommendations"].append(
                        "Enable knowledge network for better agent collaboration"
                    )

        return analysis

    def generate_master_report(self) -> Dict[str, Any]:
        """Generate comprehensive master report."""
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()

        # Count total tests
        total_tests = 0
        total_passed = 0
        total_failed = 0

        for test_suite, results in self.results.items():
            if "detailed_report" in results:
                summary = results["detailed_report"].get("summary", {})
                total_tests += summary.get("total_tests", 0)
                total_passed += summary.get("passed", 0)
                total_failed += summary.get("failed", 0)

        # Master AI analysis
        master_ai_analysis = self.analyze_master_ai_performance()

        # System health
        system_health = {
            "database_initialization": "Unknown",
            "api_endpoints": "Unknown",
            "agent_system": "Unknown"
        }

        if "registration" in self.results:
            reg_report = self.results["registration"].get("detailed_report", {})
            if reg_report.get("summary", {}).get("passed", 0) > 0:
                system_health["database_initialization"] = "Healthy"
                system_health["api_endpoints"] = "Healthy"

        if "agent_interactions" in self.results:
            agent_report = self.results["agent_interactions"].get("detailed_report", {})
            if agent_report.get("summary", {}).get("passed", 0) > 0:
                system_health["agent_system"] = "Healthy"

        master_report = {
            "test_execution": {
                "start_time": self.start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "total_duration_seconds": total_duration,
                "base_url": self.base_url
            },
            "overall_summary": {
                "total_tests": total_tests,
                "total_passed": total_passed,
                "total_failed": total_failed,
                "success_rate": f"{(total_passed/total_tests*100) if total_tests > 0 else 0:.1f}%",
                "all_tests_passed": total_failed == 0
            },
            "system_health": system_health,
            "test_suites": {
                "registration_flow": self.results.get("registration", {}),
                "agent_interactions": self.results.get("agent_interactions", {})
            },
            "master_ai_analysis": master_ai_analysis,
            "key_findings": self.generate_key_findings(),
            "recommendations": self.generate_recommendations()
        }

        return master_report

    def generate_key_findings(self) -> List[str]:
        """Generate key findings from all tests."""
        findings = []

        # Check registration
        if "registration" in self.results:
            reg_report = self.results["registration"].get("detailed_report", {})
            reg_summary = reg_report.get("summary", {})
            if reg_summary.get("passed", 0) > 0:
                findings.append("✅ User registration system is working correctly")
                findings.append("✅ Database tables are properly initialized")

            created_users = len(reg_report.get("created_users", []))
            if created_users > 0:
                findings.append(f"✅ Successfully created {created_users} test users")

        # Check agent interactions
        if "agent_interactions" in self.results:
            agent_report = self.results["agent_interactions"].get("detailed_report", {})
            capabilities = agent_report.get("capabilities_verified", {})

            if capabilities.get("personal_agent_conversation"):
                findings.append("✅ Personal AI agents can engage in conversation")

            if capabilities.get("company_agent_operations"):
                findings.append("✅ Company AI agents can create job postings")

            if capabilities.get("master_ai_matching"):
                findings.append("✅ Master AI successfully coordinates agent matching")

            if capabilities.get("multi_agent_collaboration"):
                findings.append("✅ Multiple agents can collaborate through Master AI")

        return findings

    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []

        # Check for failures
        if "registration" in self.results:
            if not self.results["registration"].get("success"):
                recommendations.append(
                    "⚠️ Registration tests failed - check database initialization and API endpoints"
                )

        if "agent_interactions" in self.results:
            agent_report = self.results["agent_interactions"].get("detailed_report", {})
            capabilities = agent_report.get("capabilities_verified", {})

            if not capabilities.get("agent_messaging"):
                recommendations.append(
                    "💡 Consider implementing direct agent-to-agent messaging for better communication"
                )

            if not capabilities.get("knowledge_sharing"):
                recommendations.append(
                    "💡 Enable knowledge network sharing for improved agent collaboration"
                )

        # Add Master AI recommendations
        if "agent_interactions" in self.results:
            master_ai_analysis = self.analyze_master_ai_performance()
            recommendations.extend(master_ai_analysis.get("recommendations", []))

        if not recommendations:
            recommendations.append("✅ All systems operational - no immediate recommendations")

        return recommendations

    def print_master_report(self, report: Dict[str, Any]):
        """Print formatted master report."""
        print("\n" + "=" * 80)
        print("COMPREHENSIVE TEST REPORT")
        print("=" * 80)
        print(f"Test Date: {report['test_execution']['end_time']}")
        print(f"Duration: {report['test_execution']['total_duration_seconds']:.2f} seconds")
        print(f"API URL: {report['test_execution']['base_url']}")
        print()

        print("OVERALL SUMMARY")
        print("-" * 80)
        summary = report['overall_summary']
        print(f"Total Tests:    {summary['total_tests']}")
        print(f"Passed:         {summary['total_passed']} ✅")
        print(f"Failed:         {summary['total_failed']} {'❌' if summary['total_failed'] > 0 else ''}")
        print(f"Success Rate:   {summary['success_rate']}")
        print(f"Status:         {'ALL TESTS PASSED ✅' if summary['all_tests_passed'] else 'SOME TESTS FAILED ❌'}")
        print()

        print("SYSTEM HEALTH")
        print("-" * 80)
        for component, status in report['system_health'].items():
            icon = "✅" if status == "Healthy" else "❓"
            print(f"{icon} {component.replace('_', ' ').title()}: {status}")
        print()

        print("MASTER AI ANALYSIS")
        print("-" * 80)
        master_ai = report['master_ai_analysis']
        print(f"Coordination Effectiveness: {master_ai['coordination_effectiveness']}")
        print(f"Agent Orchestration:        {master_ai['agent_orchestration']}")
        print(f"Knowledge Distribution:     {master_ai['knowledge_distribution']}")
        print(f"Matching Accuracy:          {master_ai['matching_accuracy']}")
        print()

        if report['key_findings']:
            print("KEY FINDINGS")
            print("-" * 80)
            for finding in report['key_findings']:
                print(finding)
            print()

        if report['recommendations']:
            print("RECOMMENDATIONS")
            print("-" * 80)
            for rec in report['recommendations']:
                print(rec)
            print()

        print("=" * 80)

    def run_all_tests(self):
        """Run all test suites."""
        print("=" * 80)
        print("COMPREHENSIVE TEST SUITE RUNNER")
        print("=" * 80)
        print(f"Target API: {self.base_url}")
        print(f"Start Time: {self.start_time.isoformat()}")
        print("=" * 80)

        # Run registration tests
        print("\n[1/2] Running Registration Flow Tests...")
        self.results["registration"] = self.run_registration_tests()
        time.sleep(2)

        # Run agent interaction tests
        print("\n[2/2] Running Agent Interaction Tests...")
        self.results["agent_interactions"] = self.run_agent_interaction_tests()

        # Generate and save master report
        master_report = self.generate_master_report()

        # Save to file
        with open("comprehensive_test_report.json", "w") as f:
            json.dump(master_report, f, indent=2)

        # Print summary
        self.print_master_report(master_report)

        print(f"\n📄 Comprehensive report saved to: comprehensive_test_report.json")
        print(f"📄 Registration report: registration_test_report.json")
        print(f"📄 Agent interaction report: agent_interaction_test_report.json")

        # Return exit code
        return 0 if master_report['overall_summary']['all_tests_passed'] else 1


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run comprehensive test suite")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)"
    )
    args = parser.parse_args()

    runner = ComprehensiveTestRunner(base_url=args.url)
    exit_code = runner.run_all_tests()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
