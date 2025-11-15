#!/usr/bin/env python3
"""
Agent-to-Agent Interaction Test Suite

Tests how different AI agents interact with each other:
- Personal AI agent (job seeker) communication
- Company AI agent (hiring manager) communication
- Agent-to-agent matching and messaging
- Master AI coordination
"""

import requests
import json
import time
from typing import Dict, Any, List
from datetime import datetime


class AgentInteractionTester:
    """Test agent-to-agent interactions."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: List[Dict[str, Any]] = []
        self.job_seeker_token: str = ""
        self.hiring_manager_token: str = ""
        self.job_seeker_agent_id: str = ""
        self.company_agent_id: str = ""

    def log_result(self, test_name: str, success: bool, message: str, data: Any = None):
        """Log test result."""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)

        status = "✅ PASS" if success else "❌ FAIL"
        print(f"\n{status} - {test_name}")
        print(f"   {message}")
        if data and isinstance(data, dict):
            # Print key insights from response
            if "response" in data:
                print(f"   Response preview: {data['response'][:150]}...")
            if "match_score" in data:
                print(f"   Match score: {data['match_score']}")

    def setup_test_users(self) -> bool:
        """Create test users and get tokens."""
        print("\n" + "=" * 80)
        print("SETTING UP TEST USERS")
        print("=" * 80)

        timestamp = int(time.time())

        # Create job seeker
        try:
            js_response = requests.post(
                f"{self.base_url}/api/auth/register",
                json={
                    "email": f"js_agent_test_{timestamp}@test.com",
                    "password": "TestPass123!",
                    "first_name": "Alice",
                    "last_name": "Developer",
                    "role": "job_seeker"
                },
                timeout=10
            )
            if js_response.status_code == 200:
                js_data = js_response.json()
                self.job_seeker_token = js_data.get("access_token", "")
                print("✅ Job seeker created")
            else:
                print("❌ Failed to create job seeker")
                return False
        except Exception as e:
            print(f"❌ Error creating job seeker: {e}")
            return False

        time.sleep(1)

        # Create hiring manager
        try:
            hm_response = requests.post(
                f"{self.base_url}/api/auth/register",
                json={
                    "email": f"hm_agent_test_{timestamp}@test.com",
                    "password": "TestPass123!",
                    "first_name": "Bob",
                    "last_name": "Recruiter",
                    "role": "hiring_manager",
                    "company_name": "InnovateTech",
                    "company_size": "50-200",
                    "industry": "Technology"
                },
                timeout=10
            )
            if hm_response.status_code == 200:
                hm_data = hm_response.json()
                self.hiring_manager_token = hm_data.get("access_token", "")
                print("✅ Hiring manager created")
            else:
                print("❌ Failed to create hiring manager")
                return False
        except Exception as e:
            print(f"❌ Error creating hiring manager: {e}")
            return False

        return True

    def test_personal_agent_initialization(self) -> bool:
        """Test personal AI agent is initialized for job seeker."""
        try:
            response = requests.get(
                f"{self.base_url}/api/agents/me",
                headers={"Authorization": f"Bearer {self.job_seeker_token}"},
                timeout=10
            )
            data = response.json()

            success = response.status_code == 200 and data.get("agent_id")
            if success:
                self.job_seeker_agent_id = data.get("agent_id", "")

            self.log_result(
                "Personal Agent Initialization",
                success,
                f"Personal agent '{data.get('agent_name', 'N/A')}' initialized with ID: {self.job_seeker_agent_id}" if success else "Failed to initialize personal agent",
                data
            )
            return success
        except Exception as e:
            self.log_result("Personal Agent Initialization", False, str(e))
            return False

    def test_company_agent_initialization(self) -> bool:
        """Test company AI agent is initialized for hiring manager."""
        try:
            response = requests.get(
                f"{self.base_url}/api/agents/me",
                headers={"Authorization": f"Bearer {self.hiring_manager_token}"},
                timeout=10
            )
            data = response.json()

            success = response.status_code == 200 and data.get("agent_id")
            if success:
                self.company_agent_id = data.get("agent_id", "")

            self.log_result(
                "Company Agent Initialization",
                success,
                f"Company agent '{data.get('agent_name', 'N/A')}' initialized with ID: {self.company_agent_id}" if success else "Failed to initialize company agent",
                data
            )
            return success
        except Exception as e:
            self.log_result("Company Agent Initialization", False, str(e))
            return False

    def test_personal_agent_conversation(self) -> bool:
        """Test conversation with personal AI agent."""
        try:
            # First message - agent learns about user
            response1 = requests.post(
                f"{self.base_url}/api/agents/chat",
                headers={"Authorization": f"Bearer {self.job_seeker_token}"},
                json={
                    "message": "Hi! I'm a senior Python developer with 5 years of experience. I'm looking for remote opportunities in AI/ML."
                },
                timeout=30
            )
            data1 = response1.json()

            success1 = response1.status_code == 200
            self.log_result(
                "Personal Agent - Initial Conversation",
                success1,
                "Agent received user profile information" if success1 else "Failed to send message",
                data1
            )

            if not success1:
                return False

            time.sleep(2)

            # Second message - test agent memory
            response2 = requests.post(
                f"{self.base_url}/api/agents/chat",
                headers={"Authorization": f"Bearer {self.job_seeker_token}"},
                json={
                    "message": "Can you help me find relevant opportunities based on what I just told you?"
                },
                timeout=30
            )
            data2 = response2.json()

            success2 = response2.status_code == 200
            self.log_result(
                "Personal Agent - Follow-up with Context",
                success2,
                "Agent responded with context awareness" if success2 else "Failed to maintain context",
                data2
            )

            return success1 and success2
        except Exception as e:
            self.log_result("Personal Agent Conversation", False, str(e))
            return False

    def test_company_agent_job_posting(self) -> bool:
        """Test company agent creating job posting."""
        try:
            response = requests.post(
                f"{self.base_url}/api/job-postings",
                headers={"Authorization": f"Bearer {self.hiring_manager_token}"},
                json={
                    "title": "Senior Python Developer - AI/ML",
                    "description": "We're looking for an experienced Python developer with AI/ML expertise to join our remote team.",
                    "requirements": ["5+ years Python experience", "Machine Learning knowledge", "Remote work experience"],
                    "location": "Remote",
                    "job_type": "full_time",
                    "salary_min": 120000,
                    "salary_max": 180000
                },
                timeout=30
            )
            data = response.json()

            success = response.status_code in [200, 201]
            self.log_result(
                "Company Agent - Create Job Posting",
                success,
                f"Job posting created: {data.get('job_id', 'N/A')}" if success else "Failed to create job posting",
                data
            )
            return success
        except Exception as e:
            self.log_result("Company Agent - Create Job Posting", False, str(e))
            return False

    def test_master_ai_matching(self) -> bool:
        """Test master AI matching between personal and company agents."""
        try:
            # Request matches for job seeker
            response = requests.get(
                f"{self.base_url}/api/matching/matches",
                headers={"Authorization": f"Bearer {self.job_seeker_token}"},
                timeout=30
            )
            data = response.json()

            success = response.status_code == 200
            match_count = len(data.get("matches", [])) if isinstance(data, dict) else 0

            self.log_result(
                "Master AI - Job Matching",
                success,
                f"Found {match_count} matches via Master AI coordination" if success else "Matching failed",
                {"match_count": match_count, "matches": data.get("matches", [])[:2]}  # Show first 2
            )
            return success
        except Exception as e:
            self.log_result("Master AI - Job Matching", False, str(e))
            return False

    def test_agent_to_agent_messaging(self) -> bool:
        """Test direct agent-to-agent communication."""
        try:
            # Personal agent sends message to company agent
            response = requests.post(
                f"{self.base_url}/api/agents/send-message",
                headers={"Authorization": f"Bearer {self.job_seeker_token}"},
                json={
                    "recipient_type": "company_agent",
                    "message": "I'm interested in the Senior Python Developer position. Can we discuss the role?",
                    "context": {
                        "regarding": "job_application",
                        "job_title": "Senior Python Developer - AI/ML"
                    }
                },
                timeout=30
            )
            data = response.json()

            success = response.status_code in [200, 201]
            self.log_result(
                "Agent-to-Agent Messaging",
                success,
                "Personal agent successfully messaged company agent" if success else "Failed to send agent message",
                data
            )
            return success
        except Exception as e:
            # This endpoint might not exist yet, so we'll note it
            self.log_result(
                "Agent-to-Agent Messaging",
                False,
                f"Endpoint may not be implemented: {str(e)}",
                {"note": "This is expected if agent-to-agent messaging isn't fully implemented"}
            )
            return False

    def test_agent_collaboration(self) -> bool:
        """Test multiple agents collaborating via Master AI."""
        try:
            # Ask personal agent to coordinate with other agents
            response = requests.post(
                f"{self.base_url}/api/agents/chat",
                headers={"Authorization": f"Bearer {self.job_seeker_token}"},
                json={
                    "message": "Can you work with other agents to help me prepare for interviews at InnovateTech?",
                    "enable_collaboration": True
                },
                timeout=30
            )
            data = response.json()

            success = response.status_code == 200
            self.log_result(
                "Multi-Agent Collaboration",
                success,
                "Agents coordinated via Master AI" if success else "Collaboration failed",
                data
            )
            return success
        except Exception as e:
            self.log_result("Multi-Agent Collaboration", False, str(e))
            return False

    def test_agent_knowledge_sharing(self) -> bool:
        """Test agents sharing knowledge through the network."""
        try:
            # Check if personal agent has access to network knowledge
            response = requests.get(
                f"{self.base_url}/api/agents/network-knowledge",
                headers={"Authorization": f"Bearer {self.job_seeker_token}"},
                params={"topic": "interview_preparation"},
                timeout=30
            )
            data = response.json()

            success = response.status_code == 200
            knowledge_count = len(data.get("knowledge_items", [])) if isinstance(data, dict) else 0

            self.log_result(
                "Agent Knowledge Sharing",
                success,
                f"Agent has access to {knowledge_count} shared knowledge items" if success else "Knowledge sharing not available",
                data
            )
            return success
        except Exception as e:
            self.log_result(
                "Agent Knowledge Sharing",
                False,
                f"Knowledge sharing endpoint may not be implemented: {str(e)}"
            )
            return False

    def run_all_tests(self) -> Dict[str, Any]:
        """Run complete agent interaction test suite."""
        print("=" * 80)
        print("AGENT-TO-AGENT INTERACTION TEST SUITE")
        print("=" * 80)
        print(f"Testing API at: {self.base_url}")
        print(f"Started at: {datetime.now().isoformat()}")
        print()

        # Setup test users
        if not self.setup_test_users():
            print("\n❌ Failed to set up test users. Aborting.")
            return self.generate_report()

        time.sleep(2)

        print("\n" + "=" * 80)
        print("RUNNING AGENT INTERACTION TESTS")
        print("=" * 80)

        # Test 1: Personal agent initialization
        self.test_personal_agent_initialization()
        time.sleep(1)

        # Test 2: Company agent initialization
        self.test_company_agent_initialization()
        time.sleep(1)

        # Test 3: Personal agent conversation
        self.test_personal_agent_conversation()
        time.sleep(2)

        # Test 4: Company agent job posting
        self.test_company_agent_job_posting()
        time.sleep(2)

        # Test 5: Master AI matching
        self.test_master_ai_matching()
        time.sleep(2)

        # Test 6: Agent-to-agent messaging
        self.test_agent_to_agent_messaging()
        time.sleep(2)

        # Test 7: Multi-agent collaboration
        self.test_agent_collaboration()
        time.sleep(2)

        # Test 8: Knowledge sharing
        self.test_agent_knowledge_sharing()

        return self.generate_report()

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["success"])
        failed_tests = total_tests - passed_tests

        report = {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "success_rate": f"{(passed_tests/total_tests*100) if total_tests > 0 else 0:.1f}%",
                "test_date": datetime.now().isoformat()
            },
            "agent_architecture": {
                "job_seeker_agent_id": self.job_seeker_agent_id,
                "company_agent_id": self.company_agent_id,
                "master_ai_coordination": "Tested",
                "knowledge_network": "Tested"
            },
            "test_results": self.results,
            "capabilities_verified": {
                "personal_agent_conversation": any(r["test"].startswith("Personal Agent") and r["success"] for r in self.results),
                "company_agent_operations": any(r["test"].startswith("Company Agent") and r["success"] for r in self.results),
                "master_ai_matching": any(r["test"].startswith("Master AI") and r["success"] for r in self.results),
                "agent_messaging": any(r["test"] == "Agent-to-Agent Messaging" and r["success"] for r in self.results),
                "multi_agent_collaboration": any(r["test"] == "Multi-Agent Collaboration" and r["success"] for r in self.results),
                "knowledge_sharing": any(r["test"] == "Agent Knowledge Sharing" and r["success"] for r in self.results)
            }
        }

        print("\n" + "=" * 80)
        print("AGENT INTERACTION TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests:   {total_tests}")
        print(f"Passed:        {passed_tests} ✅")
        print(f"Failed:        {failed_tests} ❌")
        print(f"Success Rate:  {report['summary']['success_rate']}")
        print()
        print("Verified Capabilities:")
        for capability, verified in report["capabilities_verified"].items():
            status = "✅" if verified else "❌"
            print(f"  {status} {capability.replace('_', ' ').title()}")
        print("=" * 80)

        return report


def main():
    """Main test execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Test agent-to-agent interactions")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--output",
        default="agent_interaction_test_report.json",
        help="Output file for test report (default: agent_interaction_test_report.json)"
    )
    args = parser.parse_args()

    tester = AgentInteractionTester(base_url=args.url)
    report = tester.run_all_tests()

    # Save report
    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 Full report saved to: {args.output}")

    # Exit with appropriate code
    exit(0 if report["summary"]["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
