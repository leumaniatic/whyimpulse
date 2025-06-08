from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import asyncio
import re
import json
import aiohttp
import math

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# API Keys
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
KEEPA_API_KEY = os.environ.get('KEEPA_API_KEY')

# Keepa API Client
class KeepaClient:
    def __init__(self):
        self.api_key = KEEPA_API_KEY
        self.base_url = "https://api.keepa.com"
        
    async def get_product_data(self, asin: str, domain: int = 1) -> Dict:
        """Get product data from Keepa API"""
        url = f"{self.base_url}/product"
        params = {
            "key": self.api_key,
            "domain": domain,
            "asin": asin,
            "stats": 1,
            "history": 1,
            "offers": 20
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logging.error(f"Keepa API error: {response.status}")
                    return {}
    
    async def search_products(self, query: str, domain: int = 1, limit: int = 10) -> Dict:
        """Search for alternative products"""
        url = f"{self.base_url}/search"
        params = {
            "key": self.api_key,
            "domain": domain,
            "type": "product",
            "term": query,
            "limit": limit,
            "sort": "price"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logging.error(f"Keepa search error: {response.status}")
                    return {}
    
    def parse_price_history(self, product_data: Dict) -> List[Dict]:
        """Parse price history from Keepa response"""
        if not product_data.get("products"):
            return []
        
        product = product_data["products"][0]
        csv_data = product.get("csv", [])
        
        if len(csv_data) < 2:
            return []
        
        # Keepa time format: minutes since epoch (January 1, 2011, 00:00 UTC)
        keepa_epoch = datetime(2011, 1, 1)
        
        price_history = []
        for i in range(0, len(csv_data), 2):
            if i + 1 < len(csv_data):
                timestamp_minutes = csv_data[i]
                price_cents = csv_data[i + 1]
                
                # Ensure we have valid numeric values
                if (timestamp_minutes is not None and price_cents is not None and 
                    timestamp_minutes != -1 and price_cents != -1 and
                    isinstance(timestamp_minutes, (int, float)) and isinstance(price_cents, (int, float))):
                    
                    try:
                        timestamp = keepa_epoch + timedelta(minutes=int(timestamp_minutes))
                        price = float(price_cents) / 100.0  # Convert cents to dollars
                        
                        price_history.append({
                            "timestamp": timestamp.isoformat(),
                            "price": price,
                            "date": timestamp.strftime("%Y-%m-%d")
                        })
                    except (ValueError, TypeError, OverflowError) as e:
                        logging.warning(f"Error parsing price data point: {e}")
                        continue
        
        return sorted(price_history, key=lambda x: x["timestamp"])
    
    def calculate_deal_quality(self, current_price: float, price_history: List[Dict]) -> Dict:
        """Calculate comprehensive deal quality"""
        if not price_history or current_price <= 0:
            return {
                "quality": "unknown", 
                "score": 0, 
                "current_price": current_price,
                "average_price": current_price,
                "min_price": current_price,
                "max_price": current_price,
                "percentile": 50.0,
                "savings_percent": 0.0,
                "trend": "unknown",
                "volatility": 0.0,
                "analysis": "Insufficient data for deal analysis"
            }
        
        prices = [entry["price"] for entry in price_history if entry["price"] > 0]
        if not prices:
            return {
                "quality": "unknown", 
                "score": 0, 
                "current_price": current_price,
                "average_price": current_price,
                "min_price": current_price,
                "max_price": current_price,
                "percentile": 50.0,
                "savings_percent": 0.0,
                "trend": "unknown",
                "volatility": 0.0,
                "analysis": "No valid price data for analysis"
            }
        
        # Calculate statistics
        avg_price = sum(prices) / len(prices)
        min_price = min(prices)
        max_price = max(prices)
        
        # Calculate percentile position
        sorted_prices = sorted(prices)
        position = sum(1 for p in sorted_prices if p <= current_price) / len(sorted_prices)
        
        # Recent trend analysis (last 30 days)
        recent_cutoff = datetime.now() - timedelta(days=30)
        recent_prices = [
            entry["price"] for entry in price_history 
            if datetime.fromisoformat(entry["timestamp"]) >= recent_cutoff and entry["price"] > 0
        ]
        
        trend = "stable"
        if len(recent_prices) >= 2:
            price_change = (recent_prices[-1] - recent_prices[0]) / recent_prices[0] * 100
            if price_change > 10:
                trend = "increasing"
            elif price_change < -10:
                trend = "decreasing"
        
        # Volatility calculation
        if len(prices) > 1:
            price_variance = sum((p - avg_price) ** 2 for p in prices) / len(prices)
            volatility = math.sqrt(price_variance) / avg_price * 100
        else:
            volatility = 0
        
        # Determine deal quality with sophisticated scoring
        savings_percent = ((avg_price - current_price) / avg_price) * 100
        
        if position <= 0.05:  # Bottom 5%
            quality = "excellent"
            score = 95 + min(5, savings_percent * 0.2)
        elif position <= 0.15:  # Bottom 15%
            quality = "very good"
            score = 85 + min(10, savings_percent * 0.3)
        elif position <= 0.3:  # Bottom 30%
            quality = "good"
            score = 70 + min(15, savings_percent * 0.5)
        elif position <= 0.6:  # Bottom 60%
            quality = "fair"
            score = 50 + min(20, savings_percent * 0.7)
        else:
            quality = "poor"
            score = max(10, 30 - (position - 0.6) * 50)
        
        # Adjust for trend
        if trend == "increasing":
            score = max(score - 10, 10)
        elif trend == "decreasing":
            score = min(score + 5, 100)
        
        return {
            "quality": quality,
            "score": int(score),
            "current_price": current_price,
            "average_price": round(avg_price, 2),
            "min_price": min_price,
            "max_price": max_price,
            "percentile": round(position * 100, 1),
            "savings_percent": round(savings_percent, 1),
            "trend": trend,
            "volatility": round(volatility, 1),
            "analysis": self._generate_deal_analysis(quality, savings_percent, trend)
        }
    
    def _generate_deal_analysis(self, quality: str, savings_percent: float, trend: str) -> str:
        """Generate human-readable deal analysis"""
        base_messages = {
            "excellent": "Outstanding deal! This is one of the lowest prices we've seen.",
            "very good": "Great deal! Significantly below average price.",
            "good": "Good deal! Price is below the typical range.",
            "fair": "Decent price, but you might find better deals waiting.",
            "poor": "Price is above average. Consider waiting for a better deal."
        }
        
        message = base_messages.get(quality, "Unable to analyze deal quality.")
        
        if trend == "increasing":
            message += " However, prices have been rising recently, so this might be your best option for now."
        elif trend == "decreasing":
            message += " Prices have been falling recently, so even better deals might be coming."
        
        if savings_percent > 20:
            message += f" You're saving {abs(savings_percent):.1f}% compared to the average price!"
        elif savings_percent < -20:
            message += f" This is {abs(savings_percent):.1f}% above the average price."
        
        return message
    
    def detect_price_inflation(self, price_history: List[Dict], days: int = 30) -> Dict:
        """Detect recent price manipulation"""
        if len(price_history) < 2:
            return {"inflation_detected": False, "analysis": "Insufficient data"}
        
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_entries = [
            entry for entry in price_history 
            if datetime.fromisoformat(entry["timestamp"]) >= cutoff_date
        ]
        
        if len(recent_entries) < 2:
            return {"inflation_detected": False, "analysis": "Insufficient recent data"}
        
        # Calculate inflation rate
        oldest_recent = recent_entries[0]["price"]
        newest_recent = recent_entries[-1]["price"]
        inflation_rate = ((newest_recent - oldest_recent) / oldest_recent) * 100
        
        # Detect artificial spikes
        all_prices = [entry["price"] for entry in price_history]
        avg_price = sum(all_prices) / len(all_prices)
        recent_avg = sum(entry["price"] for entry in recent_entries) / len(recent_entries)
        
        spike_factor = (recent_avg - avg_price) / avg_price * 100
        
        # Determine if inflation is suspicious
        is_suspicious = inflation_rate > 15 or spike_factor > 25
        
        analysis = ""
        if is_suspicious:
            analysis = f"⚠️ Suspicious price activity detected! "
            if inflation_rate > 15:
                analysis += f"Price increased {inflation_rate:.1f}% in {days} days. "
            if spike_factor > 25:
                analysis += f"Recent average is {spike_factor:.1f}% above historical average. "
            analysis += "This could be artificial inflation before a 'sale'."
        else:
            analysis = "No significant price manipulation detected in recent period."
        
        return {
            "inflation_detected": is_suspicious,
            "inflation_rate": round(inflation_rate, 1),
            "spike_factor": round(spike_factor, 1),
            "period_days": days,
            "start_price": oldest_recent,
            "end_price": newest_recent,
            "analysis": analysis
        }

keepa_client = KeepaClient()

# Enhanced Models
class ProductData(BaseModel):
    title: str
    price: Optional[str] = None
    image_url: Optional[str] = None
    rating: Optional[str] = None
    review_count: Optional[str] = None
    availability: Optional[str] = None
    asin: Optional[str] = None

class PriceHistory(BaseModel):
    timestamp: str
    price: float
    date: str

class DealAnalysis(BaseModel):
    quality: str
    score: int
    current_price: float
    average_price: float
    min_price: float
    max_price: float
    percentile: float
    savings_percent: float
    trend: str
    volatility: float
    analysis: str

class InflationAnalysis(BaseModel):
    inflation_detected: bool
    inflation_rate: float
    spike_factor: float
    period_days: int
    start_price: float
    end_price: float
    analysis: str

class Alternative(BaseModel):
    title: str
    price: float
    rating: Optional[float] = None
    review_count: Optional[int] = None
    asin: str
    affiliate_url: str
    savings: float
    why_better: str

class EnhancedProductAnalysis(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str
    asin: str
    product_data: ProductData
    price_history: List[PriceHistory]
    deal_analysis: DealAnalysis
    inflation_analysis: InflationAnalysis
    alternatives: List[Alternative]
    verdict: str
    pros: List[str]
    cons: List[str]
    impulse_score: int
    impulse_factors: Dict[str, Any]
    recommendation: str
    confidence_score: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ProductAnalysisRequest(BaseModel):
    amazon_url: str

# Helper Functions
def extract_asin_from_url(url: str) -> Optional[str]:
    """Extract ASIN from Amazon URL"""
    patterns = [
        r'/dp/([A-Z0-9]{10})',
        r'/gp/product/([A-Z0-9]{10})',
        r'asin=([A-Z0-9]{10})',
        r'/([A-Z0-9]{10})/?(?:\?|$)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def extract_amazon_product_data(url: str) -> ProductData:
    """Enhanced Amazon scraper with ASIN extraction"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    asin = extract_asin_from_url(url)
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract title
        title_selectors = [
            '#productTitle',
            '.product-title',
            'h1.a-size-large',
            'h1'
        ]
        title = None
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text().strip()
                break
        
        # Extract price
        price_selectors = [
            '.a-price-whole',
            '.a-price .a-offscreen',
            '.a-price-current',
            '.a-price',
            '.pricePerUnit'
        ]
        price = None
        for selector in price_selectors:
            element = soup.select_one(selector)
            if element:
                price = element.get_text().strip()
                break
        
        # Extract image
        image_selectors = [
            '#landingImage',
            '.a-dynamic-image',
            '#imgBlkFront',
            '.itemPhoto img'
        ]
        image_url = None
        for selector in image_selectors:
            element = soup.select_one(selector)
            if element:
                image_url = element.get('src') or element.get('data-src')
                break
        
        # Extract rating
        rating_selectors = [
            '.a-icon-alt',
            '.reviewCountTextLinkedHistogram',
            '.a-star-medium'
        ]
        rating = None
        for selector in rating_selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text().strip()
                rating_match = re.search(r'(\d+\.?\d*)\s*out of', text)
                if rating_match:
                    rating = rating_match.group(1)
                    break
        
        # Extract review count
        review_count = None
        review_selectors = [
            '#acrCustomerReviewText',
            '.a-link-normal'
        ]
        for selector in review_selectors:
            element = soup.select_one(selector)
            if element and 'rating' in element.get_text().lower():
                text = element.get_text().strip()
                count_match = re.search(r'([\d,]+)', text)
                if count_match:
                    review_count = count_match.group(1)
                    break
        
        # Extract availability
        availability_selectors = [
            '#availability span',
            '.a-color-success',
            '.a-color-state'
        ]
        availability = None
        for selector in availability_selectors:
            element = soup.select_one(selector)
            if element:
                availability = element.get_text().strip()
                break
        
        return ProductData(
            title=title or "Product title not found",
            price=price,
            image_url=image_url,
            rating=rating,
            review_count=review_count,
            availability=availability,
            asin=asin
        )
        
    except Exception as e:
        logging.error(f"Error scraping Amazon: {e}")
        return ProductData(
            title="Unable to extract product data",
            price=None,
            image_url=None,
            rating=None,
            review_count=None,
            availability=None,
            asin=asin
        )

def calculate_impulse_score(product_data: ProductData, price_history: List[Dict], 
                          deal_analysis: Dict, inflation_analysis: Dict) -> tuple[int, Dict]:
    """Calculate sophisticated impulse score with detailed factors"""
    factors = {
        "price_manipulation": 0,
        "scarcity_tactics": 0,
        "emotional_triggers": 0,
        "urgency_language": 0,
        "deal_authenticity": 0,
        "volatility_factor": 0
    }
    
    # Price manipulation factor (0-30 points)
    if inflation_analysis.get("inflation_detected", False):
        factors["price_manipulation"] = 25
        if inflation_analysis.get("spike_factor", 0) > 30:
            factors["price_manipulation"] = 30
    
    # Deal authenticity factor (0-25 points) - inverted, high scores are bad
    deal_quality = deal_analysis.get("quality", "unknown")
    if deal_quality == "poor":
        factors["deal_authenticity"] = 25
    elif deal_quality == "fair":
        factors["deal_authenticity"] = 15
    elif deal_quality in ["good", "very good"]:
        factors["deal_authenticity"] = 5
    else:  # excellent
        factors["deal_authenticity"] = 0
    
    # Scarcity and urgency language analysis
    title = product_data.title.lower()
    availability = (product_data.availability or "").lower()
    
    scarcity_words = ["limited", "only", "left", "hurry", "while supplies last", "limited time", 
                     "exclusive", "rare", "last chance", "final", "clearance"]
    urgency_words = ["today only", "24 hours", "flash sale", "lightning deal", "ends soon",
                    "hurry", "now", "immediate", "instant", "quick"]
    emotional_words = ["amazing", "incredible", "unbelievable", "fantastic", "revolutionary",
                      "life-changing", "must-have", "essential", "perfect", "ultimate"]
    
    # Scarcity factor (0-20 points)
    scarcity_count = sum(1 for word in scarcity_words if word in title or word in availability)
    factors["scarcity_tactics"] = min(20, scarcity_count * 5)
    
    # Urgency factor (0-15 points)
    urgency_count = sum(1 for word in urgency_words if word in title or word in availability)
    factors["urgency_language"] = min(15, urgency_count * 5)
    
    # Emotional triggers (0-10 points)
    emotional_count = sum(1 for word in emotional_words if word in title)
    factors["emotional_triggers"] = min(10, emotional_count * 2)
    
    # Volatility factor (0-10 points)
    volatility = deal_analysis.get("volatility", 0)
    if volatility > 20:
        factors["volatility_factor"] = 10
    elif volatility > 10:
        factors["volatility_factor"] = 5
    
    # Calculate total impulse score
    total_score = sum(factors.values())
    
    # Add context-based adjustments
    if "sale" in title or "deal" in title:
        total_score += 5
    
    if product_data.review_count:
        try:
            review_num = int(product_data.review_count.replace(",", ""))
            if review_num < 50:  # Low review count increases impulse risk
                total_score += 5
        except:
            pass
    
    return min(100, max(0, total_score)), factors

async def find_alternatives(product_title: str, current_price: float, asin: str) -> List[Alternative]:
    """Find better/cheaper alternatives using Keepa search"""
    try:
        # Extract key terms from title for search
        search_terms = re.sub(r'[^\w\s]', '', product_title.lower())
        search_query = ' '.join(search_terms.split()[:4])  # First 4 words
        
        search_results = await keepa_client.search_products(search_query, limit=10)
        
        alternatives = []
        if search_results.get("asinList"):
            for alt_asin in search_results["asinList"][:5]:  # Top 5 alternatives
                if alt_asin == asin:  # Skip the same product
                    continue
                
                try:
                    alt_data = await keepa_client.get_product_data(alt_asin)
                    if alt_data.get("products"):
                        alt_product = alt_data["products"][0]
                        alt_title = alt_product.get("title", "Alternative Product")
                        
                        # Get current price from price history
                        alt_history = keepa_client.parse_price_history(alt_data)
                        if alt_history:
                            alt_price = alt_history[-1]["price"]
                            savings = current_price - alt_price
                            
                            if savings > 0:  # Only include if it's cheaper
                                alternatives.append(Alternative(
                                    title=alt_title,
                                    price=alt_price,
                                    rating=alt_product.get("avgRating", 0) / 10 if alt_product.get("avgRating") else None,
                                    review_count=alt_product.get("reviewCount"),
                                    asin=alt_asin,
                                    affiliate_url=f"https://amazon.com/dp/{alt_asin}?tag=impulse-20",
                                    savings=round(savings, 2),
                                    why_better=f"${savings:.2f} cheaper with similar features"
                                ))
                except Exception as e:
                    logging.error(f"Error fetching alternative {alt_asin}: {e}")
                    continue
        
        return sorted(alternatives, key=lambda x: x.savings, reverse=True)[:3]
        
    except Exception as e:
        logging.error(f"Error finding alternatives: {e}")
        return []

async def analyze_with_enhanced_gpt4(product_data: ProductData, price_history: List[Dict],
                                   deal_analysis: Dict, inflation_analysis: Dict,
                                   alternatives: List[Alternative], impulse_score: int) -> dict:
    """Enhanced GPT-4 analysis with all historical and market context"""
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        chat = LlmChat(
            api_key=OPENAI_API_KEY,
            session_id=f"enhanced-analysis-{uuid.uuid4()}",
            system_message="""You are an expert purchasing analyst with access to comprehensive market data. 
            Analyze products using historical pricing, market trends, and psychological factors to provide 
            the most accurate buying recommendations.
            
            Return your analysis in this EXACT JSON format:
            {
                "verdict": "BUY/WAIT/SKIP with specific reasoning",
                "pros": ["specific pro1", "specific pro2", "specific pro3"],
                "cons": ["specific con1", "specific con2", "specific con3"], 
                "recommendation": "Detailed recommendation with market context and timing advice",
                "confidence_score": 1-100
            }
            
            Consider:
            - Historical price trends and volatility
            - Deal authenticity vs artificial sales
            - Alternative products and market competition
            - Psychological manipulation factors
            - Optimal timing for purchase"""
        ).with_model("openai", "gpt-4o")
        
        # Prepare comprehensive context
        price_context = ""
        if price_history:
            recent_prices = price_history[-5:]
            price_list = [f"${p['price']}" for p in recent_prices]
            price_context = f"Recent price history: {', '.join(price_list)}"
        
        alternatives_context = ""
        if alternatives:
            alt_list = [f"{alt.title} at ${alt.price} (saves ${alt.savings})" for alt in alternatives]
            alternatives_context = f"Cheaper alternatives available: {', '.join(alt_list)}"
        
        analysis_prompt = f"""
        COMPREHENSIVE PRODUCT ANALYSIS REQUEST:
        
        PRODUCT: {product_data.title}
        Current Price: {product_data.price or 'Unknown'}
        Rating: {product_data.rating or 'Unknown'} ({product_data.review_count or 'Unknown'} reviews)
        Availability: {product_data.availability or 'Unknown'}
        
        HISTORICAL PRICING DATA:
        Deal Quality: {deal_analysis.get('quality', 'unknown')} (Score: {deal_analysis.get('score', 0)}/100)
        Price vs Average: {deal_analysis.get('savings_percent', 0):.1f}% savings
        Price Trend: {deal_analysis.get('trend', 'unknown')}
        Price Volatility: {deal_analysis.get('volatility', 0):.1f}%
        {price_context}
        
        MARKET MANIPULATION ANALYSIS:
        Inflation Detected: {inflation_analysis.get('inflation_detected', False)}
        Recent Price Change: {inflation_analysis.get('inflation_rate', 0):.1f}%
        Analysis: {inflation_analysis.get('analysis', 'No analysis available')}
        
        IMPULSE PURCHASE RISK:
        Impulse Score: {impulse_score}/100 (higher = more manipulative)
        
        COMPETITIVE LANDSCAPE:
        {alternatives_context or 'No cheaper alternatives found'}
        
        TASK: Provide a sophisticated buying recommendation considering:
        1. Deal authenticity (is this a real deal or artificial markup?)
        2. Market timing (is this the right time to buy?)
        3. Alternative options (are there better choices?)
        4. Value proposition (is this product worth the price?)
        5. Risk factors (what could go wrong?)
        
        Be specific about timing, alternatives, and reasoning.
        """
        
        user_message = UserMessage(text=analysis_prompt)
        response = await chat.send_message(user_message)
        
        # Parse JSON response
        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end != 0:
                json_str = response[json_start:json_end]
                analysis = json.loads(json_str)
            else:
                # Fallback parsing
                analysis = {
                    "verdict": "ANALYZE MANUALLY - AI analysis incomplete",
                    "pros": ["Product data available", "Multiple data sources analyzed"],
                    "cons": ["Analysis parsing error", "Recommend manual review"],
                    "recommendation": response[:500] + "..." if len(response) > 500 else response,
                    "confidence_score": 50
                }
        except json.JSONDecodeError:
            analysis = {
                "verdict": "REVIEW REQUIRED - Complex analysis available",
                "pros": ["Comprehensive data analyzed", "Historical pricing available"],
                "cons": ["Analysis requires interpretation", "Multiple factors considered"],
                "recommendation": response[:500] + "..." if len(response) > 500 else response,
                "confidence_score": 60
            }
            
        return analysis
        
    except Exception as e:
        logging.error(f"Error with enhanced GPT-4 analysis: {e}")
        return {
            "verdict": "WAIT - Analysis temporarily unavailable",
            "pros": ["Product URL provided", "Basic data extracted"],
            "cons": ["Enhanced analysis unavailable", "Limited recommendation"],
            "recommendation": f"Unable to perform comprehensive analysis. Basic product data: {product_data.title}. Please try again later.",
            "confidence_score": 30
        }

# Enhanced API Routes
@api_router.get("/")
async def root():
    return {"message": "Enhanced Impulse Saver API with Keepa integration is running!"}

@api_router.post("/analyze", response_model=EnhancedProductAnalysis)
async def analyze_product_enhanced(request: ProductAnalysisRequest):
    """Enhanced product analysis with historical pricing and market intelligence"""
    try:
        # Validate Amazon URL
        if 'amazon.' not in request.amazon_url.lower():
            raise HTTPException(status_code=400, detail="Please provide a valid Amazon URL")
        
        # Extract ASIN
        asin = extract_asin_from_url(request.amazon_url)
        if not asin:
            raise HTTPException(status_code=400, detail="Could not extract product ASIN from URL")
        
        # Extract basic product data from Amazon
        product_data = extract_amazon_product_data(request.amazon_url)
        
        # Get historical data from Keepa
        keepa_data = await keepa_client.get_product_data(asin)
        price_history = keepa_client.parse_price_history(keepa_data)
        
        # Calculate current price for analysis
        current_price = 0
        if price_history:
            current_price = price_history[-1]["price"]
        elif product_data.price:
            # Try to extract price from scraped data
            price_match = re.search(r'[\d,]+\.?\d*', product_data.price.replace('$', ''))
            if price_match:
                current_price = float(price_match.group().replace(',', ''))
        
        # Perform deal analysis
        deal_analysis = keepa_client.calculate_deal_quality(current_price, price_history)
        inflation_analysis = keepa_client.detect_price_inflation(price_history)
        
        # Calculate impulse score
        impulse_score, impulse_factors = calculate_impulse_score(
            product_data, price_history, deal_analysis, inflation_analysis
        )
        
        # Find alternatives
        alternatives = await find_alternatives(product_data.title, current_price, asin)
        
        # Enhanced GPT-4 analysis
        analysis = await analyze_with_enhanced_gpt4(
            product_data, price_history, deal_analysis, inflation_analysis, 
            alternatives, impulse_score
        )
        
        # Create comprehensive analysis object
        result = EnhancedProductAnalysis(
            url=request.amazon_url,
            asin=asin,
            product_data=product_data,
            price_history=[PriceHistory(**p) for p in price_history[-30:]],  # Last 30 data points
            deal_analysis=DealAnalysis(**deal_analysis),
            inflation_analysis=InflationAnalysis(**inflation_analysis),
            alternatives=alternatives,
            verdict=analysis["verdict"],
            pros=analysis["pros"],
            cons=analysis["cons"],
            impulse_score=impulse_score,
            impulse_factors=impulse_factors,
            recommendation=analysis["recommendation"],
            confidence_score=analysis.get("confidence_score", 75)
        )
        
        # Save to database
        await db.enhanced_analyses.insert_one(result.dict())
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in enhanced analysis: {e}")
        raise HTTPException(status_code=500, detail="Error performing enhanced analysis. Please try again.")

@api_router.get("/recent-analyses", response_model=List[EnhancedProductAnalysis])
async def get_recent_enhanced_analyses(limit: int = 10):
    """Get recent enhanced analyses"""
    try:
        analyses = await db.enhanced_analyses.find().sort("timestamp", -1).limit(limit).to_list(limit)
        return [EnhancedProductAnalysis(**analysis) for analysis in analyses]
    except Exception as e:
        logging.error(f"Error fetching enhanced analyses: {e}")
        return []

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
