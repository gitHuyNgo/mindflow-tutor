import requests
import sys
import json
from datetime import datetime
from typing import Dict, Any

class MindFlowAPITester:
    def __init__(self, base_url="https://mindflow-tutor.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_base = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.session_id = "test_session_123"
        self.results = []

    def log_test(self, name: str, success: bool, response_data: Dict[Any, Any] = None, error: str = None):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test_name": name,
            "success": success,
            "response": response_data,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        self.results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if error:
            print(f"   Error: {error}")
        if response_data:
            print(f"   Response: {json.dumps(response_data, indent=2)[:200]}...")

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int = 200, 
                 data: Dict[Any, Any] = None, params: Dict[Any, Any] = None) -> tuple:
        """Run a single API test"""
        url = f"{self.api_base}/{endpoint.lstrip('/')}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                if data:
                    response = requests.post(url, json=data, headers=headers, params=params, timeout=30)
                else:
                    response = requests.post(url, headers=headers, params=params, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            try:
                response_data = response.json() if response.text else {}
            except:
                response_data = {"raw_response": response.text}
                
            error = None if success else f"Expected {expected_status}, got {response.status_code}"
            
            self.log_test(name, success, response_data, error)
            return success, response_data

        except Exception as e:
            error_msg = f"Request failed: {str(e)}"
            self.log_test(name, False, None, error_msg)
            return False, {}

    def test_health_endpoint(self):
        """Test the health endpoint"""
        print("\n🔍 Testing Health Endpoint...")
        return self.run_test("Health Check", "GET", "/health")

    def test_root_endpoint(self):
        """Test root API endpoint"""
        print("\n🔍 Testing Root API Endpoint...")
        return self.run_test("Root API Check", "GET", "/")

    def test_agora_config_endpoint(self):
        """Test Agora config endpoint"""
        print("\n🔍 Testing Agora Config Endpoint...")
        return self.run_test("Agora Config", "GET", "/v1/agora/config")

    def test_status_endpoint(self):
        """Test the status endpoint"""
        print("\n🔍 Testing Status Endpoint...")
        return self.run_test("System Status", "GET", "/v1/status")

    def test_ask_endpoint(self):
        """Test the ask endpoint with a simple question"""
        print("\n🔍 Testing Ask Endpoint...")
        test_question = "What is machine learning?"
        params = {
            "question": test_question,
            "session_id": self.session_id
        }
        return self.run_test("Ask Question", "POST", "/v1/ask", params=params)

    def test_documents_list_endpoint(self):
        """Test the documents list endpoint"""
        print("\n🔍 Testing Documents List Endpoint...")
        return self.run_test("List Documents", "GET", "/v1/documents")

    def test_conversations_list_endpoint(self):
        """Test the conversations list endpoint"""  
        print("\n🔍 Testing Conversations List Endpoint...")
        return self.run_test("List Conversations", "GET", "/v1/conversations")

    def test_search_endpoint(self):
        """Test the web search endpoint"""
        print("\n🔍 Testing Search Endpoint...")
        data = {
            "query": "Python programming basics",
            "max_results": 3
        }
        return self.run_test("Web Search", "POST", "/v1/search", data=data)

    def test_process_trigger_endpoint(self):
        """Test the process trigger endpoint (may fail due to missing screen capture)"""
        print("\n🔍 Testing Process Trigger Endpoint...")
        data = {
            "screen_capture": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "session_id": self.session_id,
            "user_query": "Help me understand this",
            "emotion_state": "confused"
        }
        return self.run_test("Process Trigger", "POST", "/v1/process-trigger", data=data)

    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting MindFlow Tutor Backend Tests...")
        print(f"📍 Testing API at: {self.api_base}")
        
        # Test specific endpoints from review request first
        self.test_health_endpoint()
        self.test_root_endpoint() 
        self.test_agora_config_endpoint()
        self.test_status_endpoint()
        self.test_documents_list_endpoint()
        
        # Test additional core functionality
        self.test_ask_endpoint()
        self.test_conversations_list_endpoint()
        self.test_search_endpoint()
        
        # Test trigger endpoint (may fail)
        self.test_process_trigger_endpoint()
        
        self.print_summary()
        return self.tests_passed == self.tests_run

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*50)
        print("📊 TEST SUMMARY")
        print("="*50)
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_run - self.tests_passed}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed < self.tests_run:
            print("\n❌ Failed Tests:")
            for result in self.results:
                if not result["success"]:
                    print(f"   • {result['test_name']}: {result['error']}")
        
        print("\n" + "="*50)

def main():
    tester = MindFlowAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())