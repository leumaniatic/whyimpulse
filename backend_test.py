
import requests
import sys
import time
import json
from datetime import datetime

class EnhancedImpulseSaverAPITester:
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

    def validate_enhanced_features(self, response):
        """Validate the enhanced features in the response"""
        validation_results = []
        
        # 1. Historical Price Analysis
        if "price_history" in response and isinstance(response["price_history"], list):
            if len(response["price_history"]) > 0:
                validation_results.append("✅ Historical price data is present")
                
                # Check price history structure
                price_point = response["price_history"][0]
                if all(key in price_point for key in ["timestamp", "price", "date"]):
                    validation_results.append("✅ Price history data structure is valid")
                else:
                    validation_results.append("❌ Price history data structure is incomplete")
            else:
                validation_results.append("⚠️ Price history array is empty")
        else:
            validation_results.append("❌ Historical price data is missing")
        
        # 2. Deal Analysis
        if "deal_analysis" in response and isinstance(response["deal_analysis"], dict):
            deal_analysis = response["deal_analysis"]
            required_deal_fields = [
                "quality", "score", "current_price", "average_price", 
                "min_price", "max_price", "percentile", "savings_percent",
                "trend", "volatility", "analysis"
            ]
            
            missing_deal_fields = [field for field in required_deal_fields if field not in deal_analysis]
            
            if not missing_deal_fields:
                validation_results.append("✅ Deal analysis data is complete")
                
                # Check deal quality value
                if deal_analysis["quality"] in ["excellent", "very good", "good", "fair", "poor", "unknown"]:
                    validation_results.append("✅ Deal quality classification is valid")
                else:
                    validation_results.append(f"❌ Invalid deal quality: {deal_analysis['quality']}")
                
                # Check price trend
                if deal_analysis["trend"] in ["increasing", "decreasing", "stable"]:
                    validation_results.append("✅ Price trend analysis is valid")
                else:
                    validation_results.append(f"❌ Invalid price trend: {deal_analysis['trend']}")
            else:
                validation_results.append(f"❌ Deal analysis is missing fields: {', '.join(missing_deal_fields)}")
        else:
            validation_results.append("❌ Deal analysis data is missing")
        
        # 3. Price Manipulation Detection
        if "inflation_analysis" in response and isinstance(response["inflation_analysis"], dict):
            inflation_analysis = response["inflation_analysis"]
            required_inflation_fields = [
                "inflation_detected", "inflation_rate", "spike_factor", 
                "period_days", "start_price", "end_price", "analysis"
            ]
            
            missing_inflation_fields = [field for field in required_inflation_fields if field not in inflation_analysis]
            
            if not missing_inflation_fields:
                validation_results.append("✅ Price manipulation detection data is complete")
                
                # Check inflation detection boolean
                if isinstance(inflation_analysis["inflation_detected"], bool):
                    validation_results.append("✅ Inflation detection flag is valid")
                else:
                    validation_results.append("❌ Inflation detection flag is not a boolean")
            else:
                validation_results.append(f"❌ Price manipulation analysis is missing fields: {', '.join(missing_inflation_fields)}")
        else:
            validation_results.append("❌ Price manipulation detection data is missing")
        
        # 4. Smart Alternatives
        if "alternatives" in response and isinstance(response["alternatives"], list):
            if len(response["alternatives"]) > 0:
                validation_results.append("✅ Product alternatives are present")
                
                # Check alternative structure
                alternative = response["alternatives"][0]
                required_alt_fields = ["title", "price", "asin", "affiliate_url", "savings", "why_better"]
                
                missing_alt_fields = [field for field in required_alt_fields if field not in alternative]
                
                if not missing_alt_fields:
                    validation_results.append("✅ Alternative product data structure is valid")
                else:
                    validation_results.append(f"❌ Alternative product data is missing fields: {', '.join(missing_alt_fields)}")
            else:
                validation_results.append("⚠️ No alternative products found")
        else:
            validation_results.append("❌ Product alternatives data is missing")
        
        # 5. Advanced Impulse Scoring
        if "impulse_factors" in response and isinstance(response["impulse_factors"], dict):
            impulse_factors = response["impulse_factors"]
            required_factor_fields = [
                "price_manipulation", "scarcity_tactics", "emotional_triggers",
                "urgency_language", "deal_authenticity", "volatility_factor"
            ]
            
            missing_factor_fields = [field for field in required_factor_fields if field not in impulse_factors]
            
            if not missing_factor_fields:
                validation_results.append("✅ Impulse factor breakdown is complete")
            else:
                validation_results.append(f"❌ Impulse factor breakdown is missing fields: {', '.join(missing_factor_fields)}")
        else:
            validation_results.append("❌ Impulse factor breakdown is missing")
        
        # Print validation results
        print("\n📋 Enhanced Features Validation:")
        for result in validation_results:
            print(result)
        
        # Return overall validation success
        return all(result.startswith("✅") for result in validation_results)

def main():
    print("="*50)
    print("🧪 ENHANCED IMPULSE SAVER API TEST SUITE")
    print("="*50)
    
    # Setup tester
    tester = EnhancedImpulseSaverAPITester()
    
    # Test API root
    tester.test_api_root()
    
    # Test with valid Amazon URLs that should have rich historical data
    test_urls = [
        "https://www.amazon.com/Apple-iPhone-15-Pro-256GB/dp/B0CHX1K3R7",  # iPhone 15 Pro
        "https://www.amazon.com/Sony-WH-1000XM5-Canceling-Wireless-Headphones/dp/B09XS7JWHH",  # Sony WH-1000XM5
        "https://www.amazon.com/dp/B08N5WRWNW",  # Example from the requirements
        "https://www.amazon.com/Samsung-Unlocked-Smartphone-Intelligent-Graphite/dp/B0CRBHPQ1F",  # Samsung Galaxy S24
        "https://www.amazon.com/Kindle-Paperwhite-16-adjustable-lighting/dp/B08KTZ8249"  # Kindle Paperwhite
    ]
    
    # Test with one valid URL first
    print("\n🔍 Testing with popular product that should have extensive price history...")
    success, response = tester.test_analyze_product(test_urls[0])
    
    # If first test succeeded, check enhanced features
    if success:
        print("\n📋 Validating enhanced features...")
        tester.validate_enhanced_features(response)
        
        # Check basic response structure
        required_fields = [
            "id", "url", "asin", "product_data", "price_history", "deal_analysis",
            "inflation_analysis", "alternatives", "verdict", "pros", "cons",
            "impulse_score", "impulse_factors", "recommendation", "confidence_score"
        ]
        
        missing_fields = [field for field in required_fields if field not in response]
        
        if missing_fields:
            print(f"❌ Missing fields in response: {', '.join(missing_fields)}")
        else:
            print("✅ Response structure is valid")
        
        # Test with another product to verify consistency
        print("\n🔍 Testing with another product for consistency...")
        tester.test_analyze_product(test_urls[1])
    
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
      