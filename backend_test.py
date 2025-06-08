
import requests
import sys
import time
import json
from datetime import datetime

class ImpulseSaverAPITester:
    def __init__(self, base_url="https://e581c80c-36c8-433f-9fe0-c7f8897a053a.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status, data=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")

            success = response.status_code == expected_status
            
            result = {
                "name": name,
                "url": url,
                "method": method,
                "expected_status": expected_status,
                "actual_status": response.status_code,
                "success": success
            }
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                if response.text:
                    try:
                        result["response"] = response.json()
                    except:
                        result["response"] = response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                if response.text:
                    try:
                        result["error"] = response.json()
                    except:
                        result["error"] = response.text
            
            self.test_results.append(result)
            return success, response.json() if success and response.text else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.test_results.append({
                "name": name,
                "url": url,
                "method": method,
                "success": False,
                "error": str(e)
            })
            return False, {}

    def test_api_root(self):
        """Test the API root endpoint"""
        return self.run_test(
            "API Root",
            "GET",
            "",
            200
        )

    def test_analyze_product(self, amazon_url):
        """Test product analysis endpoint"""
        return self.run_test(
            "Product Analysis",
            "POST",
            "analyze",
            200,
            data={"amazon_url": amazon_url}
        )
    
    def test_invalid_url(self, url):
        """Test with invalid URL"""
        return self.run_test(
            "Invalid URL Validation",
            "POST",
            "analyze",
            400,
            data={"amazon_url": url}
        )
    
    def test_recent_analyses(self):
        """Test recent analyses endpoint"""
        return self.run_test(
            "Recent Analyses",
            "GET",
            "recent-analyses",
            200
        )

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*50)
        print(f"📊 TEST SUMMARY: {self.tests_passed}/{self.tests_run} tests passed")
        print("="*50)
        
        for result in self.test_results:
            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            print(f"{status} - {result['name']} ({result['method']} {result['url']})")
        
        print("="*50)
        return self.tests_passed == self.tests_run

def main():
    print("="*50)
    print("🧪 IMPULSE SAVER API TEST SUITE")
    print("="*50)
    
    # Setup tester
    tester = ImpulseSaverAPITester()
    
    # Test API root
    tester.test_api_root()
    
    # Test with valid Amazon URLs
    test_urls = [
        "https://www.amazon.com/Apple-iPhone-13-128GB-Blue/dp/B09G9HD6PD",
        "https://www.amazon.com/Sony-WH-1000XM4-Canceling-Headphones-phone-call/dp/B0863TXGM3",
        "https://www.amazon.com/dp/B08N5WRWNW"  # Example from the requirements
    ]
    
    # Test with one valid URL (to save time)
    success, response = tester.test_analyze_product(test_urls[0])
    
    # If first test succeeded, check response structure
    if success:
        print("\n📋 Validating response structure...")
        required_fields = [
            "id", "url", "product_data", "verdict", 
            "pros", "cons", "impulse_score", "recommendation"
        ]
        
        missing_fields = [field for field in required_fields if field not in response]
        
        if missing_fields:
            print(f"❌ Missing fields in response: {', '.join(missing_fields)}")
        else:
            print("✅ Response structure is valid")
            
            # Check product_data structure
            product_data = response.get("product_data", {})
            product_fields = ["title", "price", "image_url", "rating", "review_count", "availability"]
            
            missing_product_fields = [field for field in product_fields if field not in product_data]
            if missing_product_fields:
                print(f"⚠️ Some product data fields are missing: {', '.join(missing_product_fields)}")
            
            # Check impulse score range
            impulse_score = response.get("impulse_score")
            if impulse_score is not None:
                if 1 <= impulse_score <= 100:
                    print(f"✅ Impulse score is within valid range: {impulse_score}")
                else:
                    print(f"❌ Impulse score out of range (1-100): {impulse_score}")
    
    # Test with invalid URLs
    tester.test_invalid_url("https://example.com/product")
    tester.test_invalid_url("not-a-url")
    
    # Test recent analyses endpoint
    tester.test_recent_analyses()
    
    # Print summary
    success = tester.print_summary()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
      