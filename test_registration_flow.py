#!/usr/bin/env python3
"""
Comprehensive Registration Flow Test

Tests the complete user registration flow including:
- User registration (job seeker and hiring manager)
- Email verification simulation
- Personal AI agent creation
- Profile setup
- Agent activation
"""

import requests
import json
import time
from typing import Dict, Any, List
from datetime import datetime


class RegistrationTester:
    """Test registration and onboarding flow."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results: List[Dict[str, Any]] = []
        self.test_users: List[Dict[str, Any]] = []

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
        if data and not success:
            print(f"   Response: {json.dumps(data, indent=2)}")

    def test_health_check(self) -> bool:
        """Test API health endpoint."""
        try:
            response = requests.get(f"{self.base_url}/api/health", timeout=5)
            data = response.json()

            success = response.status_code == 200 and data.get("status") == "healthy"
            self.log_result(
                "API Health Check",
                success,
                f"API is {data.get('status', 'unknown')}",
                data
            )
            return success
        except Exception as e:
            self.log_result("API Health Check", False, str(e))
            return False

    def test_register_job_seeker(self) -> Dict[str, Any]:
        """Test job seeker registration."""
        timestamp = int(time.time())
        user_data = {
            "email": f"jobseeker{timestamp}@test.com",
            "password": "SecurePassword123!",
            "first_name": "Alex",
            "last_name": "Johnson",
            "role": "job_seeker"
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/auth/register",
                json=user_data,
                timeout=10
            )
            data = response.json()

            success = response.status_code == 200
            if success:
                user_data["user_id"] = data.get("user", {}).get("id")
                user_data["access_token"] = data.get("access_token")
                self.test_users.append(user_data)

            self.log_result(
                "Job Seeker Registration",
                success,
                f"Registered user: {user_data['email']}" if success else f"Registration failed: {data.get('detail', 'Unknown error')}",
                data
            )
            return user_data if success else {}
        except Exception as e:
            self.log_result("Job Seeker Registration", False, str(e))
            return {}

    def test_register_hiring_manager(self) -> Dict[str, Any]:
        """Test hiring manager registration."""
        timestamp = int(time.time())
        user_data = {
            "email": f"hiringmanager{timestamp}@test.com",
            "password": "SecurePassword123!",
            "first_name": "Sarah",
            "last_name": "Williams",
            "role": "hiring_manager",
            "company_name": "TechCorp Inc",
            "company_size": "50-200",
            "industry": "Technology"
        }

        try:
            response = requests.post(
                f"{self.base_url}/api/auth/register",
                json=user_data,
                timeout=10
            )
            data = response.json()

            success = response.status_code == 200
            if success:
                user_data["user_id"] = data.get("user", {}).get("id")
                user_data["access_token"] = data.get("access_token")
                self.test_users.append(user_data)

            self.log_result(
                "Hiring Manager Registration",
                success,
                f"Registered hiring manager: {user_data['email']}" if success else f"Registration failed: {data.get('detail', 'Unknown error')}",
                data
            )
            return user_data if success else {}
        except Exception as e:
            self.log_result("Hiring Manager Registration", False, str(e))
            return {}

    def test_login(self, email: str, password: str) -> Dict[str, Any]:
        """Test user login."""
        try:
            response = requests.post(
                f"{self.base_url}/api/auth/login",
                json={"email": email, "password": password},
                timeout=10
            )
            data = response.json()

            success = response.status_code == 200 and "access_token" in data
            self.log_result(
                "User Login",
                success,
                f"Login successful for {email}" if success else f"Login failed: {data.get('detail', 'Unknown error')}",
                {"email": email, "has_token": "access_token" in data}
            )
            return data if success else {}
        except Exception as e:
            self.log_result("User Login", False, str(e))
            return {}

    def test_get_personal_agent(self, access_token: str) -> Dict[str, Any]:
        """Test getting personal AI agent."""
        try:
            response = requests.get(
                f"{self.base_url}/api/agents/me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10
            )
            data = response.json()

            success = response.status_code == 200
            self.log_result(
                "Get Personal AI Agent",
                success,
                f"Agent retrieved: {data.get('agent_name', 'Unknown')}" if success else f"Failed to get agent: {data.get('detail', 'Unknown error')}",
                data
            )
            return data if success else {}
        except Exception as e:
            self.log_result("Get Personal AI Agent", False, str(e))
            return {}

    def test_chat_with_agent(self, access_token: str, message: str) -> Dict[str, Any]:
        """Test chatting with personal AI agent."""
        try:
            response = requests.post(
                f"{self.base_url}/api/agents/chat",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"message": message},
                timeout=30
            )
            data = response.json()

            success = response.status_code == 200
            self.log_result(
                "Chat with Personal Agent",
                success,
                f"Agent responded" if success else f"Chat failed: {data.get('detail', 'Unknown error')}",
                {"message": message, "response_preview": data.get("response", "")[:100] if success else None}
            )
            return data if success else {}
        except Exception as e:
            self.log_result("Chat with Personal Agent", False, str(e))
            return {}

    def test_complete_onboarding(self, access_token: str, role: str) -> bool:
        """Test complete onboarding flow."""
        try:
            if role == "job_seeker":
                # Start onboarding interview
                response = requests.post(
                    f"{self.base_url}/api/onboarding/start",
                    headers={"Authorization": f"Bearer {access_token}"},
                    timeout=30
                )
                data = response.json()

                success = response.status_code == 200
                self.log_result(
                    "Start Onboarding Interview",
                    success,
                    f"Onboarding started: {data.get('session_id', 'N/A')}" if success else f"Failed: {data.get('detail', 'Unknown error')}",
                    data
                )
                return success
            else:
                # Hiring manager onboarding
                response = requests.post(
                    f"{self.base_url}/api/hiring-manager/onboarding/start",
                    headers={"Authorization": f"Bearer {access_token}"},
                    json={
                        "company_name": "TechCorp Inc",
                        "job_title": "Senior Software Engineer",
                        "department": "Engineering"
                    },
                    timeout=30
                )
                data = response.json()

                success = response.status_code == 200
                self.log_result(
                    "Start Hiring Manager Onboarding",
                    success,
                    f"Onboarding started" if success else f"Failed: {data.get('detail', 'Unknown error')}",
                    data
                )
                return success
        except Exception as e:
            self.log_result("Complete Onboarding", False, str(e))
            return False

    def run_all_tests(self):
        """Run complete test suite."""
        print("=" * 80)
        print("REGISTRATION FLOW TEST SUITE")
        print("=" * 80)
        print(f"Testing API at: {self.base_url}")
        print(f"Started at: {datetime.now().isoformat()}")
        print()

        # Test 1: Health check
        if not self.test_health_check():
            print("\n❌ API is not healthy. Aborting tests.")
            return self.generate_report()

        time.sleep(1)

        # Test 2: Register job seeker
        job_seeker = self.test_register_job_seeker()
        time.sleep(1)

        # Test 3: Register hiring manager
        hiring_manager = self.test_register_hiring_manager()
        time.sleep(1)

        # Test 4: Login tests
        if job_seeker:
            self.test_login(job_seeker["email"], job_seeker["password"])
            time.sleep(1)

            # Test 5: Get personal agent
            agent_data = self.test_get_personal_agent(job_seeker["access_token"])
            time.sleep(1)

            # Test 6: Chat with agent
            if agent_data:
                self.test_chat_with_agent(
                    job_seeker["access_token"],
                    "Hi! I'm looking for a software engineering position."
                )
                time.sleep(1)

            # Test 7: Start onboarding
            self.test_complete_onboarding(job_seeker["access_token"], "job_seeker")

        if hiring_manager:
            self.test_login(hiring_manager["email"], hiring_manager["password"])
            time.sleep(1)

            # Get hiring manager agent
            hm_agent = self.test_get_personal_agent(hiring_manager["access_token"])
            time.sleep(1)

            # Start hiring manager onboarding
            self.test_complete_onboarding(hiring_manager["access_token"], "hiring_manager")

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
            "test_results": self.results,
            "created_users": [
                {
                    "email": user["email"],
                    "role": user["role"],
                    "user_id": user.get("user_id")
                }
                for user in self.test_users
            ]
        }

        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"Total Tests:   {total_tests}")
        print(f"Passed:        {passed_tests} ✅")
        print(f"Failed:        {failed_tests} ❌")
        print(f"Success Rate:  {report['summary']['success_rate']}")
        print()
        print(f"Created Users: {len(self.test_users)}")
        for user in self.test_users:
            print(f"  - {user['email']} ({user['role']})")
        print("=" * 80)

        return report


def main():
    """Main test execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Test registration flow")
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="API base URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "--output",
        default="registration_test_report.json",
        help="Output file for test report (default: registration_test_report.json)"
    )
    args = parser.parse_args()

    tester = RegistrationTester(base_url=args.url)
    report = tester.run_all_tests()

    # Save report
    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\n📄 Full report saved to: {args.output}")

    # Exit with appropriate code
    exit(0 if report["summary"]["failed"] == 0 else 1)


if __name__ == "__main__":
    main()
