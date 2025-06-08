
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
                required_alt_fields = ["title", "price", "asin", "affiliate_url", "amazon_url", "savings", "savings_percent", "why_better"]
                
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
                        # Check for expected alternatives: JBL Tune 760NC and Apple AirPods Max
                        alt_titles = [alt["title"] for alt in response["alternatives"]]
                        jbl_found = any("JBL Tune 760NC" in title for title in alt_titles)
                        airpods_found = any("Apple AirPods Max" in title for title in alt_titles)
                        
                        if jbl_found:
                            validation_results.append("✅ Sony test: JBL Tune 760NC alternative found")
                            
                            # Find the JBL alternative
                            jbl_alt = next((alt for alt in response["alternatives"] if "JBL Tune 760NC" in alt["title"]), None)
                            if jbl_alt:
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
                                # Check for image URL
                                if "image_url" in airpods_alt and airpods_alt["image_url"]:
                                    validation_results.append("✅ Sony test: AirPods alternative has image URL")
                                else:
                                    validation_results.append("❌ Sony test: AirPods alternative missing image URL")
                        else:
                            validation_results.append("❌ Sony test: Apple AirPods Max alternative not found")
                    
                    # Special validation for Acer laptop
                    if is_acer_laptop:
                        # Check for HP Pavilion alternative
                        hp_found = any("HP Pavilion" in alt["title"] for alt in response["alternatives"])
                        
                        if hp_found:
                            validation_results.append("✅ Acer test: HP Pavilion alternative found")
                            
                            # Find the HP alternative
                            hp_alt = next((alt for alt in response["alternatives"] if "HP Pavilion" in alt["title"]), None)
                            if hp_alt:
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

    def validate_category_features(self, response, category_name):
        """Validate category-specific features in the response"""
        validation_results = []
        
        # 1. Category Detection
        product_title = response.get("product_data", {}).get("title", "").lower()
        
        # Check if category is properly identified in the analysis
        category_detected = False
        recommendation = response.get("recommendation", "").lower()
        verdict = response.get("verdict", "").lower()
        pros = [p.lower() for p in response.get("pros", [])]
        cons = [c.lower() for c in response.get("cons", [])]
        
        # Look for category mentions in various parts of the analysis
        all_text = recommendation + " " + verdict + " " + " ".join(pros) + " " + " ".join(cons)
        
        category_keywords = {
            "electronics": ["electronics", "device", "gadget", "tech", "technology", "electronic"],
            "laptops": ["laptop", "computer", "notebook", "pc", "computing"],
            "books": ["book", "read", "author", "novel", "literature", "pages"],
            "kitchen": ["kitchen", "cooking", "cook", "food", "culinary", "brew", "coffee"],
            "beauty": ["beauty", "skin", "skincare", "moisturizer", "cream", "lotion"],
            "pet supplies": ["pet", "dog", "cat", "animal", "toy", "kong"],
            "fitness": ["fitness", "exercise", "workout", "resistance", "gym", "training"]
        }
        
        # Determine which category this product belongs to
        detected_category = None
        for cat, keywords in category_keywords.items():
            if any(keyword in product_title for keyword in keywords):
                detected_category = cat
                break
        
        # If we couldn't detect from title, try to infer from the category_name
        if not detected_category:
            for cat in category_keywords.keys():
                if cat.lower() in category_name.lower():
                    detected_category = cat
                    break
        
        if detected_category:
            # Check if the analysis mentions the correct category
            category_mentioned = any(keyword in all_text for keyword in category_keywords.get(detected_category, []))
            
            if category_mentioned:
                validation_results.append(f"✅ {category_name}: Category properly identified in analysis")
            else:
                validation_results.append(f"❌ {category_name}: Category not properly identified in analysis")
        else:
            validation_results.append(f"⚠️ {category_name}: Unable to determine expected category")
        
        # 2. Impulse Factors
        if "impulse_factors" in response and isinstance(response["impulse_factors"], dict):
            impulse_factors = response["impulse_factors"]
            required_factor_fields = [
                "price_manipulation", "scarcity_tactics", "emotional_triggers",
                "urgency_language", "deal_authenticity", "volatility_factor"
            ]
            
            missing_factor_fields = [field for field in required_factor_fields if field not in impulse_factors]
            
            if not missing_factor_fields:
                validation_results.append(f"✅ {category_name}: All 6 impulse factors present")
                
                # Check if values are meaningful (not all zeros)
                non_zero_factors = sum(1 for factor in impulse_factors.values() if factor > 0)
                if non_zero_factors > 0:
                    validation_results.append(f"✅ {category_name}: {non_zero_factors} impulse factors have meaningful values")
                else:
                    validation_results.append(f"❌ {category_name}: All impulse factors are zero")
            else:
                validation_results.append(f"❌ {category_name}: Missing impulse factors: {', '.join(missing_factor_fields)}")
        else:
            validation_results.append(f"❌ {category_name}: Impulse factors missing")
        
        # 3. Alternatives Display
        if "alternatives" in response and isinstance(response["alternatives"], list):
            if len(response["alternatives"]) > 0:
                validation_results.append(f"✅ {category_name}: Alternatives found ({len(response['alternatives'])})")
                
                # Check for product images
                alternatives_with_images = sum(1 for alt in response["alternatives"] if alt.get("image_url"))
                if alternatives_with_images == len(response["alternatives"]):
                    validation_results.append(f"✅ {category_name}: All alternatives have product images")
                elif alternatives_with_images > 0:
                    validation_results.append(f"⚠️ {category_name}: Only {alternatives_with_images}/{len(response['alternatives'])} alternatives have images")
                else:
                    validation_results.append(f"❌ {category_name}: No alternatives have product images")
                
                # Check for Amazon and affiliate links
                all_have_links = all("amazon_url" in alt and "affiliate_url" in alt for alt in response["alternatives"])
                if all_have_links:
                    validation_results.append(f"✅ {category_name}: All alternatives have Amazon and affiliate links")
                else:
                    validation_results.append(f"❌ {category_name}: Some alternatives missing Amazon or affiliate links")
                
                # Check for savings calculations
                all_have_savings = all("savings" in alt and "savings_percent" in alt for alt in response["alternatives"])
                if all_have_savings:
                    validation_results.append(f"✅ {category_name}: All alternatives have savings calculations")
                else:
                    validation_results.append(f"❌ {category_name}: Some alternatives missing savings calculations")
            else:
                validation_results.append(f"❌ {category_name}: No alternatives found")
        else:
            validation_results.append(f"❌ {category_name}: Alternatives section missing")
        
        # 4. Analysis Quality
        if "recommendation" in response and len(response.get("recommendation", "")) > 50:
            validation_results.append(f"✅ {category_name}: AI recommendation is substantial")
        else:
            validation_results.append(f"❌ {category_name}: AI recommendation is too short or missing")
        
        if "pros" in response and "cons" in response:
            if len(response["pros"]) >= 2 and len(response["cons"]) >= 2:
                validation_results.append(f"✅ {category_name}: Pros and cons are present and relevant")
            else:
                validation_results.append(f"⚠️ {category_name}: Pros or cons may be insufficient")
        else:
            validation_results.append(f"❌ {category_name}: Pros or cons missing")
        
        if "verdict" in response and len(response.get("verdict", "")) > 0:
            if any(keyword in response["verdict"].lower() for keyword in ["buy", "wait", "skip"]):
                validation_results.append(f"✅ {category_name}: Verdict is appropriate")
            else:
                validation_results.append(f"⚠️ {category_name}: Verdict format may be non-standard")
        else:
            validation_results.append(f"❌ {category_name}: Verdict missing")
        
        # 5. UI Components
        if "price_history" in response and len(response.get("price_history", [])) > 0:
            validation_results.append(f"✅ {category_name}: Price history data available for charts")
        else:
            validation_results.append(f"❌ {category_name}: Price history data missing")
        
        if "deal_analysis" in response and "quality" in response.get("deal_analysis", {}):
            validation_results.append(f"✅ {category_name}: Deal quality indicators present")
        else:
            validation_results.append(f"❌ {category_name}: Deal quality indicators missing")
        
        # Print validation results
        print(f"\n📋 {category_name.upper()} CATEGORY VALIDATION:")
        for result in validation_results:
            print(result)
        
        # Return overall validation success
        success_count = sum(1 for result in validation_results if result.startswith("✅"))
        warning_count = sum(1 for result in validation_results if result.startswith("⚠️"))
        fail_count = sum(1 for result in validation_results if result.startswith("❌"))
        
        print(f"\n📊 {category_name.upper()} SUMMARY: {success_count} passed, {warning_count} warnings, {fail_count} failed")
        
        # Consider warnings as partial success
        return {
            "category": category_name,
            "success_count": success_count,
            "warning_count": warning_count,
            "fail_count": fail_count,
            "total": len(validation_results),
            "success_rate": (success_count + (warning_count * 0.5)) / len(validation_results) if len(validation_results) > 0 else 0
        }

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
    print("🧪 ENHANCED IMPULSE SAVER PRO API TEST SUITE")
    print("="*50)
    
    # Setup tester
    tester = EnhancedImpulseSaverAPITester()
    
    # Test API root
    tester.test_api_root()
    
    # Test with valid Amazon URLs that should have rich historical data
    test_urls = [
        # 1. Electronics (Known working)
        "https://www.amazon.com/Sony-WH-1000XM4-Canceling-Headphones-phone-call/dp/B0863TXGM3",  # Sony WH-1000XM4 (specified in requirements)
        
        # 2. Laptops (Should work)
        "https://www.amazon.com/acer-Aspire-Copilot-Display-Processor/dp/B0DWNLN3KP",  # Acer laptop (specified in requirements)
        
        # 3. Books (Test new category)
        "https://www.amazon.com/Atomic-Habits-Proven-Build-Break/dp/0735211299",  # Atomic Habits
        
        # 4. Kitchen Appliances (Test new category)
        "https://www.amazon.com/COSORI-Electric-Gooseneck-Variable-Temperature/dp/B077JBQZPX",  # Coffee maker
        
        # 5. Beauty/Skincare (Test new category)
        "https://www.amazon.com/CeraVe-Moisturizing-Cream-Daily-Moisturizer/dp/B00TTD9BRC",  # CeraVe moisturizer
        
        # 6. Pet Supplies (Test new category)
        "https://www.amazon.com/KONG-Classic-Dog-Toy-Large/dp/B0002AR0II",  # KONG dog toy
        
        # 7. Fitness Equipment (Test new category)
        "https://www.amazon.com/Bodylastics-Resistance-Exercise-Snap-Guard/dp/B006NZZQJE",  # Resistance bands
        
        # 8. Amazon Short URL (Testing new functionality)
        "https://a.co/d/0PqJoaA"  # Amazon short URL for a product
    ]
    
    # Test with multiple valid URLs to ensure consistent behavior
    all_responses = []
    category_names = [
        "Electronics",
        "Laptops",
        "Books",
        "Kitchen",
        "Beauty",
        "Pet Supplies",
        "Fitness"
    ]
    
    for i, url in enumerate(test_urls):
        category = category_names[i] if i < len(category_names) else f"Category #{i+1}"
        print(f"\n🔍 Testing with {category} URL: {url}")
        success, response = tester.test_analyze_product(url)
        
        if success:
            all_responses.append(response)
            print(f"\n📋 Validating enhanced features for {category}...")
            
            # Special validation for Sony WH-1000XM4 headphones (first URL)
            is_sony_headphones = i == 0
            is_acer_laptop = i == 1
            
            if is_sony_headphones:
                print("\n🎧 VALIDATING SONY WH-1000XM4 HEADPHONES (SPECIFIED TEST PRODUCT)")
                print("Expected values from requirements:")
                print("- Current price: $228")
                print("- Average price: $272.67 (16.4% savings)")
                print("- Deal quality: 'good' (score: 78/100)")
                print("- Price range: $129.99 - $349.99")
                print("- Impulse score: 20/100 (low manipulation risk)")
                print("- Inflation detected: false")
                print("- Alternatives: JBL Tune 760NC and Apple AirPods Max with images")
                tester.validate_enhanced_features(response, is_sony_headphones=True, is_acer_laptop=False)
            
            elif is_acer_laptop:
                print("\n💻 VALIDATING ACER LAPTOP (SPECIFIED TEST PRODUCT)")
                print("Expected values from requirements:")
                print("- Deal quality: 'fair' (score: 25/100)")
                print("- Deal authenticity factor: 25/30 (others should be 0)")
                print("- Alternatives: HP Pavilion with $230 savings (26.1% off)")
                print("- Alternative should have image")
                tester.validate_enhanced_features(response, is_sony_headphones=False, is_acer_laptop=True)
            
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
            print(f"❌ Failed to analyze {category} URL")
    
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
    
    # Generate comprehensive category report
    print("\n" + "="*80)
    print("📊 COMPREHENSIVE CATEGORY SUPPORT REPORT")
    print("="*80)
    
    category_results = []
    
    # Define category names
    category_names = [
        "Electronics (Sony Headphones)",
        "Laptops (Acer)",
        "Books (Atomic Habits)",
        "Kitchen (Coffee Maker)",
        "Beauty (CeraVe)",
        "Pet Supplies (KONG)",
        "Fitness (Resistance Bands)",
        "Short URL Test"
    ]
    
    # Validate each category
    for i, response in enumerate(all_responses):
        if i < len(category_names):
            category_name = category_names[i]
            print(f"\n🔍 Analyzing category: {category_name}")
            result = tester.validate_category_features(response, category_name)
            category_results.append(result)
    
    # Print summary table
    print("\n" + "="*80)
    print("📋 CATEGORY SUPPORT SUMMARY")
    print("="*80)
    print(f"{'CATEGORY':<25} | {'SUCCESS':<10} | {'WARNING':<10} | {'FAIL':<10} | {'SCORE':<10}")
    print("-"*80)
    
    for result in category_results:
        category = result["category"]
        success = result["success_count"]
        warning = result["warning_count"]
        fail = result["fail_count"]
        score = result["success_rate"] * 100
        
        status = "✅ WORKING" if score >= 80 else "⚠️ PARTIAL" if score >= 50 else "❌ BROKEN"
        
        print(f"{category[:25]:<25} | {success:<10} | {warning:<10} | {fail:<10} | {score:.1f}% {status}")
    
    print("="*80)
    
    # Identify what's working vs what needs improvement
    working_categories = [r["category"] for r in category_results if r["success_rate"] >= 0.8]
    partial_categories = [r["category"] for r in category_results if 0.5 <= r["success_rate"] < 0.8]
    broken_categories = [r["category"] for r in category_results if r["success_rate"] < 0.5]
    
    print("\n🟢 WORKING WELL:")
    for category in working_categories:
        print(f"  - {category}")
    
    print("\n🟡 PARTIAL SUPPORT:")
    for category in partial_categories:
        print(f"  - {category}")
    
    print("\n🔴 NEEDS IMPROVEMENT:")
    for category in broken_categories:
        print(f"  - {category}")
    
    # Print summary
    success = tester.print_summary()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
