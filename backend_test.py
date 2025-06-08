
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

    def validate_enhanced_features(self, response, is_sony_headphones=False, is_acer_laptop=False):
        """Validate the enhanced features in the response"""
        validation_results = []
        
        # 1. Historical Price Analysis
        if "price_history" in response and isinstance(response["price_history"], list):
            if len(response["price_history"]) > 0:
                validation_results.append(f"✅ Historical price data is present ({len(response['price_history'])} data points)")
                
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
                    validation_results.append(f"✅ Deal quality classification is valid: {deal_analysis['quality']} (Score: {deal_analysis['score']}/100)")
                else:
                    validation_results.append(f"❌ Invalid deal quality: {deal_analysis['quality']}")
                
                # Check price trend
                if deal_analysis["trend"] in ["increasing", "decreasing", "stable"]:
                    validation_results.append("✅ Price trend analysis is valid")
                else:
                    validation_results.append(f"❌ Invalid price trend: {deal_analysis['trend']}")
                
                # Special validation for Sony headphones
                if is_sony_headphones:
                    # Validate expected values from requirements
                    expected_values = {
                        "current_price": 228,
                        "average_price": 272.67,
                        "quality": "good",
                        "score": 78,
                        "min_price": 129.99,
                        "max_price": 349.99
                    }
                    
                    for key, expected_value in expected_values.items():
                        if key in deal_analysis:
                            actual_value = deal_analysis[key]
                            # Allow for small floating point differences
                            if isinstance(expected_value, float) and isinstance(actual_value, float):
                                is_close = abs(expected_value - actual_value) < 0.5
                                if is_close:
                                    validation_results.append(f"✅ Sony test: {key} matches expected value ({actual_value})")
                                else:
                                    validation_results.append(f"❌ Sony test: {key} value {actual_value} doesn't match expected {expected_value}")
                            else:
                                if actual_value == expected_value:
                                    validation_results.append(f"✅ Sony test: {key} matches expected value ({actual_value})")
                                else:
                                    validation_results.append(f"❌ Sony test: {key} value {actual_value} doesn't match expected {expected_value}")
                
                # Special validation for Acer laptop
                if is_acer_laptop:
                    # Validate expected values from requirements
                    expected_values = {
                        "quality": "fair",
                        "score": 25
                    }
                    
                    for key, expected_value in expected_values.items():
                        if key in deal_analysis:
                            actual_value = deal_analysis[key]
                            if actual_value == expected_value:
                                validation_results.append(f"✅ Acer test: {key} matches expected value ({actual_value})")
                            else:
                                validation_results.append(f"❌ Acer test: {key} value {actual_value} doesn't match expected {expected_value}")
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
                    validation_results.append(f"✅ Inflation detection flag is valid: {inflation_analysis['inflation_detected']}")
                    
                    # Special validation for Sony headphones
                    if is_sony_headphones and inflation_analysis["inflation_detected"] == False:
                        validation_results.append("✅ Sony test: Correctly shows no price manipulation detected")
                    elif is_sony_headphones:
                        validation_results.append("❌ Sony test: Incorrectly shows price manipulation detected")
                else:
                    validation_results.append("❌ Inflation detection flag is not a boolean")
            else:
                validation_results.append(f"❌ Price manipulation analysis is missing fields: {', '.join(missing_inflation_fields)}")
        else:
            validation_results.append("❌ Price manipulation detection data is missing")
        
        # 4. Smart Alternatives
        if "alternatives" in response and isinstance(response["alternatives"], list):
            if len(response["alternatives"]) > 0:
                validation_results.append(f"✅ Product alternatives are present ({len(response['alternatives'])} alternatives)")
                
                # Check alternative structure
                alternative = response["alternatives"][0]
                required_alt_fields = ["title", "price", "asin", "affiliate_url", "amazon_url", "savings", "savings_percent", "why_better", "rating", "review_count"]
                
                missing_alt_fields = [field for field in required_alt_fields if field not in alternative]
                
                if not missing_alt_fields:
                    validation_results.append("✅ Alternative product data structure is valid")
                    
                    # Check if both direct Amazon and affiliate links are present
                    if "amazon_url" in alternative and "affiliate_url" in alternative:
                        amazon_url = alternative["amazon_url"]
                        affiliate_url = alternative["affiliate_url"]
                        
                        if amazon_url.startswith("https://amazon.com/dp/"):
                            validation_results.append("✅ Direct Amazon URL format is valid")
                        else:
                            validation_results.append(f"❌ Invalid direct Amazon URL format: {amazon_url}")
                        
                        if affiliate_url.startswith("https://amazon.com/dp/") and "tag=" in affiliate_url:
                            validation_results.append("✅ Affiliate URL format is valid")
                        else:
                            validation_results.append(f"❌ Invalid affiliate URL format: {affiliate_url}")
                    else:
                        validation_results.append("❌ Missing URL fields in alternatives")
                    
                    # Special validation for Sony headphones
                    if is_sony_headphones:
                        # Check for exactly 2 alternatives
                        if len(response["alternatives"]) == 2:
                            validation_results.append("✅ Sony test: Exactly 2 alternatives found as expected")
                            
                            # Check for expected alternatives: JBL Tune 760NC and Apple AirPods Max
                            alt_titles = [alt["title"] for alt in response["alternatives"]]
                            jbl_found = any("JBL Tune 760NC" in title for title in alt_titles)
                            airpods_found = any("Apple AirPods Max" in title for title in alt_titles)
                            
                            if jbl_found:
                                validation_results.append("✅ Sony test: JBL Tune 760NC alternative found")
                                
                                # Find the JBL alternative
                                jbl_alt = next((alt for alt in response["alternatives"] if "JBL Tune 760NC" in alt["title"]), None)
                                if jbl_alt:
                                    # Check JBL price and savings
                                    if abs(jbl_alt["price"] - 196.08) < 0.5:
                                        validation_results.append(f"✅ Sony test: JBL price matches expected value (${jbl_alt['price']})")
                                    else:
                                        validation_results.append(f"❌ Sony test: JBL price ${jbl_alt['price']} doesn't match expected $196.08")
                                    
                                    if abs(jbl_alt["savings"] - 31.92) < 0.5:
                                        validation_results.append(f"✅ Sony test: JBL savings matches expected value (${jbl_alt['savings']})")
                                    else:
                                        validation_results.append(f"❌ Sony test: JBL savings ${jbl_alt['savings']} doesn't match expected $31.92")
                                    
                                    if abs(jbl_alt["savings_percent"] - 14.0) < 0.5:
                                        validation_results.append(f"✅ Sony test: JBL savings percentage matches expected value ({jbl_alt['savings_percent']}%)")
                                    else:
                                        validation_results.append(f"❌ Sony test: JBL savings percentage {jbl_alt['savings_percent']}% doesn't match expected 14%")
                                    
                                    if abs(jbl_alt["rating"] - 5.0) < 0.1:
                                        validation_results.append(f"✅ Sony test: JBL rating matches expected value ({jbl_alt['rating']})")
                                    else:
                                        validation_results.append(f"❌ Sony test: JBL rating {jbl_alt['rating']} doesn't match expected 5.0")
                                    
                                    # Check for image URL
                                    if "image_url" in jbl_alt and jbl_alt["image_url"]:
                                        validation_results.append("✅ Sony test: JBL alternative has image URL")
                                    else:
                                        validation_results.append("❌ Sony test: JBL alternative missing image URL")
                            else:
                                validation_results.append("❌ Sony test: JBL Tune 760NC alternative not found")
                            
                            if airpods_found:
                                validation_results.append("✅ Sony test: Apple AirPods Max alternative found")
                                
                                # Find the AirPods alternative
                                airpods_alt = next((alt for alt in response["alternatives"] if "Apple AirPods Max" in alt["title"]), None)
                                if airpods_alt:
                                    # Check AirPods price and savings
                                    if abs(airpods_alt["price"] - 207.48) < 0.5:
                                        validation_results.append(f"✅ Sony test: AirPods price matches expected value (${airpods_alt['price']})")
                                    else:
                                        validation_results.append(f"❌ Sony test: AirPods price ${airpods_alt['price']} doesn't match expected $207.48")
                                    
                                    if abs(airpods_alt["savings"] - 20.52) < 0.5:
                                        validation_results.append(f"✅ Sony test: AirPods savings matches expected value (${airpods_alt['savings']})")
                                    else:
                                        validation_results.append(f"❌ Sony test: AirPods savings ${airpods_alt['savings']} doesn't match expected $20.52")
                                    
                                    if abs(airpods_alt["savings_percent"] - 9.0) < 0.5:
                                        validation_results.append(f"✅ Sony test: AirPods savings percentage matches expected value ({airpods_alt['savings_percent']}%)")
                                    else:
                                        validation_results.append(f"❌ Sony test: AirPods savings percentage {airpods_alt['savings_percent']}% doesn't match expected 9%")
                                    
                                    if abs(airpods_alt["rating"] - 4.3) < 0.1:
                                        validation_results.append(f"✅ Sony test: AirPods rating matches expected value ({airpods_alt['rating']})")
                                    else:
                                        validation_results.append(f"❌ Sony test: AirPods rating {airpods_alt['rating']} doesn't match expected 4.3")
                                    
                                    # Check for image URL
                                    if "image_url" in airpods_alt and airpods_alt["image_url"]:
                                        validation_results.append("✅ Sony test: AirPods alternative has image URL")
                                    else:
                                        validation_results.append("❌ Sony test: AirPods alternative missing image URL")
                            else:
                                validation_results.append("❌ Sony test: Apple AirPods Max alternative not found")
                        else:
                            validation_results.append(f"❌ Sony test: Found {len(response['alternatives'])} alternatives instead of expected 2")
                    
                    # Special validation for Acer laptop
                    if is_acer_laptop:
                        # Check for HP Pavilion alternative
                        hp_found = any("HP Pavilion" in alt["title"] for alt in response["alternatives"])
                        
                        if hp_found:
                            validation_results.append("✅ Acer test: HP Pavilion alternative found")
                            
                            # Find the HP alternative
                            hp_alt = next((alt for alt in response["alternatives"] if "HP Pavilion" in alt["title"]), None)
                            if hp_alt:
                                # Check HP price and savings
                                if abs(hp_alt["savings"] - 230) < 0.5:
                                    validation_results.append(f"✅ Acer test: HP savings matches expected value (${hp_alt['savings']})")
                                else:
                                    validation_results.append(f"❌ Acer test: HP savings ${hp_alt['savings']} doesn't match expected $230")
                                
                                if abs(hp_alt["savings_percent"] - 26.1) < 0.5:
                                    validation_results.append(f"✅ Acer test: HP savings percentage matches expected value ({hp_alt['savings_percent']}%)")
                                else:
                                    validation_results.append(f"❌ Acer test: HP savings percentage {hp_alt['savings_percent']}% doesn't match expected 26.1%")
                                
                                # Check for image URL
                                if "image_url" in hp_alt and hp_alt["image_url"]:
                                    validation_results.append("✅ Acer test: HP alternative has image URL")
                                else:
                                    validation_results.append("❌ Acer test: HP alternative missing image URL")
                        else:
                            validation_results.append("❌ Acer test: HP Pavilion alternative not found")
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
                
                # Special validation for Sony headphones
                if is_sony_headphones and "impulse_score" in response:
                    impulse_score = response["impulse_score"]
                    if impulse_score == 20:
                        validation_results.append("✅ Sony test: Impulse score matches expected value (20/100)")
                    else:
                        validation_results.append(f"❌ Sony test: Impulse score {impulse_score} doesn't match expected value (20/100)")
                
                # Special validation for Acer laptop
                if is_acer_laptop and "impulse_factors" in response:
                    deal_authenticity = impulse_factors.get("deal_authenticity", 0)
                    if deal_authenticity == 25:
                        validation_results.append("✅ Acer test: Deal authenticity factor matches expected value (25/30)")
                    else:
                        validation_results.append(f"❌ Acer test: Deal authenticity factor {deal_authenticity} doesn't match expected value (25/30)")
                    
                    # Check that other factors are 0
                    other_factors = ["price_manipulation", "scarcity_tactics", "emotional_triggers", 
                                    "urgency_language", "volatility_factor"]
                    all_zeros = all(impulse_factors.get(factor, -1) == 0 for factor in other_factors)
                    if all_zeros:
                        validation_results.append("✅ Acer test: All other impulse factors are 0 as expected")
                    else:
                        validation_results.append("❌ Acer test: Some impulse factors are not 0 as expected")
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
    print("🧪 ENHANCED IMPULSE SAVER PRO API TEST SUITE")
    print("="*50)
    
    # Setup tester
    tester = EnhancedImpulseSaverAPITester()
    
    # Test API root
    tester.test_api_root()
    
    # Test with valid Amazon URLs that should have rich historical data
    test_urls = [
        "https://www.amazon.com/Sony-WH-1000XM4-Canceling-Headphones-phone-call/dp/B0863TXGM3",  # Sony WH-1000XM4 (specified in requirements)
        "https://www.amazon.com/acer-Aspire-Copilot-Display-Processor/dp/B0DWNLN3KP/ref=sr_1_2_sspa?_encoding=UTF8&content-id=amzn1.sym.1d3b8f55-c47a-4b7f-a127-3409d1ca6dd1&dib=eyJ2IjoiMSJ9.DiQvAQRlLQCB5Gsx8d6OAKQdyJH2afvkWXNs41V3qFo7-nq45NCujulA4cSK-uYB3We7fDTL9qAvqRgYcLenBScgRnQjipU2mp6uQpXIza4gIvo0DjInn8pZ8t3p86n_kjHsakQ4CGuXbau2n-MbWTxTOI4KjDUSId1GcE_D8EVVlbEn3fsli_StqxG-cBLG_4bDASPquRu9WqT01DfYW-TSQd-yDXwA6eFZJ6FzOzs.iZxbUSNgjOQV-Qj2a6TXRZ9ZWW3IJl6VOk_RR_mWFAE&dib_tag=se&keywords=laptops&pd_rd_r=3fc0bf83-468d-4f3a-8096-3913ae936332&pd_rd_w=OX2sM&pd_rd_wg=pXefA&qid=1749380161&sr=8-2-spons&sp_csd=d2lkZ2V0TmFtZT1zcF9hdGY&th=1"  # Acer Laptop (specified in requirements)
    ]
    
    # Test with multiple valid URLs to ensure consistent behavior
    all_responses = []
    for i, url in enumerate(test_urls):
        print(f"\n🔍 Testing with product URL #{i+1}: {url}")
        success, response = tester.test_analyze_product(url)
        
        if success:
            all_responses.append(response)
            print(f"\n📋 Validating enhanced features for product #{i+1}...")
            
            # Special validation for Sony WH-1000XM4 headphones (first URL)
            is_sony_headphones = i == 0
            if is_sony_headphones:
                print("\n🎧 VALIDATING SONY WH-1000XM4 HEADPHONES (SPECIFIED TEST PRODUCT)")
                print("Expected values from requirements:")
                print("- Current price: $228")
                print("- Average price: $272.67 (16.4% savings)")
                print("- Deal quality: 'good' (score: 78/100)")
                print("- Price range: $129.99 - $349.99")
                print("- Impulse score: 20/100 (low manipulation risk)")
                print("- Inflation detected: false")
            
            tester.validate_enhanced_features(response, is_sony_headphones)
            
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
                
                # Validate product data structure
                product_data = response.get("product_data", {})
                product_fields = ["title", "price", "image_url", "rating", "review_count", "availability", "asin"]
                missing_product_fields = [field for field in product_fields if field not in product_data]
                
                if missing_product_fields:
                    print(f"❌ Missing product data fields: {', '.join(missing_product_fields)}")
                else:
                    print("✅ Product data structure is valid")
                
                # Validate impulse score range
                impulse_score = response.get("impulse_score", -1)
                if 0 <= impulse_score <= 100:
                    print(f"✅ Impulse score is valid: {impulse_score}/100")
                else:
                    print(f"❌ Invalid impulse score: {impulse_score}")
                
                # Validate verdict format
                verdict = response.get("verdict", "")
                if any(keyword in verdict.lower() for keyword in ["buy", "wait", "skip"]):
                    print(f"✅ Verdict format is valid: {verdict}")
                else:
                    print(f"❌ Invalid verdict format: {verdict}")
        else:
            print(f"❌ Failed to analyze product URL #{i+1}")
    
    # Compare responses to ensure consistent structure
    if len(all_responses) >= 2:
        print("\n🔄 Checking consistency across multiple product analyses...")
        first_keys = set(all_responses[0].keys())
        consistent = True
        
        for i, response in enumerate(all_responses[1:], 2):
            current_keys = set(response.keys())
            if first_keys != current_keys:
                print(f"❌ Inconsistent response structure for product #{i}")
                print(f"   Missing: {first_keys - current_keys}")
                print(f"   Extra: {current_keys - first_keys}")
                consistent = False
        
        if consistent:
            print("✅ All responses have consistent structure")
    
    # Test with invalid URLs
    print("\n🔍 Testing with invalid URLs...")
    tester.test_invalid_url("https://example.com/product")
    tester.test_invalid_url("not-a-url")
    
    # Test recent analyses endpoint
    print("\n🔍 Testing recent analyses endpoint...")
    success, recent_analyses = tester.test_recent_analyses()
    
    if success and isinstance(recent_analyses, list):
        print(f"✅ Recent analyses endpoint returned {len(recent_analyses)} items")
        
        # Check if our analyzed products appear in recent analyses
        if len(recent_analyses) > 0:
            print("✅ Recent analyses contains data")
            
            # Check structure of recent analyses
            if all(isinstance(item, dict) for item in recent_analyses):
                print("✅ Recent analyses items have valid structure")
            else:
                print("❌ Recent analyses contains invalid items")
    
    # Print summary
    success = tester.print_summary()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
      