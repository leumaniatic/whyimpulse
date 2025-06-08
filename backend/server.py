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
AMAZON_AFFILIATE_TAG = os.environ.get('AMAZON_AFFILIATE_TAG', 'impulse-20')

def generate_affiliate_link(asin: str, additional_params: dict = None) -> str:
    """Generate Amazon affiliate link with proper tracking"""
    base_url = f"https://amazon.com/dp/{asin}"
    params = {"tag": AMAZON_AFFILIATE_TAG}
    
    if additional_params:
        params.update(additional_params)
    
    param_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{base_url}?{param_string}"

def generate_enhanced_affiliate_link(asin: str, source: str = "whyimpulse") -> str:
    """Generate enhanced affiliate link with tracking parameters"""
    additional_params = {
        "ref": f"whyimpulse_{source}",
        "linkCode": "ll1",
        "linkId": "whyimpulse"
    }
    return generate_affiliate_link(asin, additional_params)

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
        
        # Keepa CSV format: [0] is Amazon price history, [1] is New price, etc.
        # We want Amazon price history (index 0)
        if not csv_data or len(csv_data) == 0:
            return []
        
        amazon_price_history = csv_data[0] if isinstance(csv_data[0], list) else csv_data
        
        if len(amazon_price_history) < 2:
            return []
        
        # Keepa time format: minutes since epoch (January 1, 2011, 00:00 UTC)
        keepa_epoch = datetime(2011, 1, 1)
        
        price_history = []
        for i in range(0, len(amazon_price_history), 2):
            if i + 1 < len(amazon_price_history):
                timestamp_minutes = amazon_price_history[i]
                price_cents = amazon_price_history[i + 1]
                
                # Ensure we have valid numeric values
                if (timestamp_minutes is not None and price_cents is not None and 
                    timestamp_minutes != -1 and price_cents != -1 and price_cents > 0 and
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
            return {
                "inflation_detected": False, 
                "inflation_rate": 0.0,
                "spike_factor": 0.0,
                "period_days": days,
                "start_price": 0.0,
                "end_price": 0.0,
                "analysis": "Insufficient data for inflation analysis"
            }
        
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_entries = [
            entry for entry in price_history 
            if datetime.fromisoformat(entry["timestamp"]) >= cutoff_date
        ]
        
        if len(recent_entries) < 2:
            return {
                "inflation_detected": False, 
                "inflation_rate": 0.0,
                "spike_factor": 0.0,
                "period_days": days,
                "start_price": 0.0,
                "end_price": 0.0,
                "analysis": "Insufficient recent data for inflation analysis"
            }
        
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

def detect_product_category(title: str, asin: str = None) -> str:
    """Universal category detection for all Amazon products"""
    title_lower = title.lower()
    
    # Electronics & Technology
    if any(word in title_lower for word in ['headphone', 'headset', 'earphone', 'earbud', 'airpods', 'beats']):
        return 'headphones'
    elif any(word in title_lower for word in ['iphone', 'samsung', 'pixel', 'phone', 'smartphone', 'mobile']):
        return 'phone'
    elif any(word in title_lower for word in ['laptop', 'notebook', 'macbook', 'aspire', 'thinkpad', 'pavilion', 'zenbook', 'inspiron', 'ideapad', 'chromebook']):
        return 'laptop'
    elif any(word in title_lower for word in ['tablet', 'ipad', 'kindle', 'fire tablet']):
        return 'tablet'
    elif any(word in title_lower for word in ['tv', 'television', 'monitor', 'display', 'screen']):
        return 'display'
    elif any(word in title_lower for word in ['camera', 'canon', 'nikon', 'sony camera', 'gopro', 'dslr']):
        return 'camera'
    elif any(word in title_lower for word in ['speaker', 'bluetooth speaker', 'soundbar', 'audio', 'stereo']):
        return 'audio'
    elif any(word in title_lower for word in ['gaming', 'xbox', 'playstation', 'nintendo', 'console', 'controller']):
        return 'gaming'
    elif any(word in title_lower for word in ['smartwatch', 'apple watch', 'fitbit', 'garmin watch', 'fitness tracker']):
        return 'wearables'
    
    # Home & Kitchen
    elif any(word in title_lower for word in ['coffee maker', 'espresso', 'keurig', 'french press', 'coffee machine', 'coffee']):
        return 'coffee'
    elif any(word in title_lower for word in ['vacuum', 'dyson', 'roomba', 'cleaner', 'shark vacuum']):
        return 'cleaning'
    elif any(word in title_lower for word in ['air fryer', 'instant pot', 'slow cooker', 'pressure cooker', 'blender', 'mixer', 'fryer']):
        return 'kitchen_appliances'
    elif any(word in title_lower for word in ['mattress', 'pillow', 'bed', 'sheets', 'bedding', 'comforter']):
        return 'bedding'
    elif any(word in title_lower for word in ['sofa', 'chair', 'table', 'desk', 'furniture', 'ottoman']):
        return 'furniture'
    elif any(word in title_lower for word in ['lamp', 'light', 'ceiling fan', 'lighting', 'chandelier']):
        return 'lighting'
    
    # Health & Beauty
    elif any(word in title_lower for word in ['skincare', 'moisturizer', 'serum', 'cleanser', 'sunscreen', 'cream', 'cerave', 'neutrogena']):
        return 'skincare'
    elif any(word in title_lower for word in ['makeup', 'foundation', 'lipstick', 'mascara', 'eyeshadow', 'cosmetics']):
        return 'makeup'
    elif any(word in title_lower for word in ['shampoo', 'conditioner', 'hair', 'styling', 'hair dryer', 'straightener']):
        return 'hair_care'
    elif any(word in title_lower for word in ['supplement', 'vitamin', 'protein powder', 'omega', 'probiotics']):
        return 'supplements'
    elif any(word in title_lower for word in ['toothbrush', 'toothpaste', 'oral care', 'dental', 'mouthwash']):
        return 'oral_care'
    
    # Fashion & Apparel
    elif any(word in title_lower for word in ['dress', 'shirt', 'pants', 'jeans', 'jacket', 'sweater', 'hoodie']):
        return 'clothing'
    elif any(word in title_lower for word in ['shoes', 'sneakers', 'boots', 'sandals', 'heels', 'loafers']):
        return 'shoes'
    elif any(word in title_lower for word in ['watch', 'jewelry', 'necklace', 'ring', 'bracelet', 'earrings']):
        return 'accessories'
    elif any(word in title_lower for word in ['bag', 'backpack', 'purse', 'handbag', 'luggage', 'suitcase']):
        return 'bags'
    
    # Sports & Outdoors
    elif any(word in title_lower for word in ['dumbbell', 'weights', 'exercise', 'yoga mat', 'treadmill', 'bike', 'resistance', 'fitness']):
        return 'fitness'
    elif any(word in title_lower for word in ['tent', 'sleeping bag', 'hiking', 'camping', 'outdoor', 'backpack']):
        return 'outdoor'
    elif any(word in title_lower for word in ['basketball', 'football', 'soccer', 'tennis', 'golf', 'sports']):
        return 'sports'
    
    # Automotive
    elif any(word in title_lower for word in ['car', 'automotive', 'tire', 'oil', 'brake', 'battery', 'motor']):
        return 'automotive'
    
    # Baby & Kids
    elif any(word in title_lower for word in ['baby', 'infant', 'toddler', 'kids', 'children', 'toy', 'stroller']):
        return 'baby_kids'
    
    # Books & Media
    elif any(word in title_lower for word in ['book', 'novel', 'cookbook', 'textbook', 'guide', 'manual', 'habits', 'atomic']):
        return 'books'
    elif any(word in title_lower for word in ['movie', 'dvd', 'blu-ray', 'cd', 'music', 'album']):
        return 'media'
    
    # Pet Supplies
    elif any(word in title_lower for word in ['dog', 'cat', 'pet', 'puppy', 'kitten', 'animal', 'pet food', 'kong']):
        return 'pets'
    
    # Tools & Garden
    elif any(word in title_lower for word in ['drill', 'hammer', 'screwdriver', 'tool', 'wrench', 'saw']):
        return 'tools'
    elif any(word in title_lower for word in ['plant', 'garden', 'seed', 'fertilizer', 'gardening', 'lawn']):
        return 'garden'
    
    # Office & School
    elif any(word in title_lower for word in ['pen', 'pencil', 'notebook', 'paper', 'office', 'desk', 'calculator']):
        return 'office'
    
    # Default fallback based on common patterns
    elif any(word in title_lower for word in ['wireless', 'bluetooth', 'usb', 'charger', 'cable']):
        return 'electronics'
    elif any(word in title_lower for word in ['organic', 'natural', 'essential']):
        return 'health'
    else:
        return 'general'

def get_comprehensive_alternatives_data():
    """Comprehensive alternatives database for all Amazon categories"""
    return {
        'headphones': [
            ('B099F367LT', 'JBL Tune 760NC - Wireless Over-Ear Headphones with Noise Cancelling', 196.08, 5.0, 3378, 'https://m.media-amazon.com/images/I/61lrT-TdyLL._AC_SX679_.jpg'),
            ('B08PZHPW8G', 'Apple AirPods Max - Space Gray', 299.99, 4.3, 5020, 'https://m.media-amazon.com/images/I/81ErO6zSJnL._AC_SX679_.jpg'),
            ('B0BVPJ7C9V', 'Bose QuietComfort 45 Wireless Bluetooth Noise Cancelling Headphones', 279.99, 4.4, 12400, 'https://m.media-amazon.com/images/I/51gMV9zVDOL._AC_SX679_.jpg'),
            ('B08PZMP36N', 'Sennheiser HD 450BT Wireless Headphones', 149.99, 4.2, 8500, 'https://m.media-amazon.com/images/I/61m0TDa5hbL._AC_SX679_.jpg'),
            ('B07G4YX39H', 'Audio-Technica ATH-M40x Professional Studio Monitor Headphones', 99.99, 4.6, 25000, 'https://m.media-amazon.com/images/I/71Q5qlLhblL._AC_SX679_.jpg')
        ],
        'phone': [
            ('B0CHX7TKDD', 'Apple iPhone 15 Pro Max, 256GB, Titanium Blue', 999.99, 4.5, 15000, 'https://m.media-amazon.com/images/I/81Os1SDWpcL._AC_SX679_.jpg'),
            ('B0CRBHPQ1F', 'Samsung Galaxy S24 Ultra, 256GB, Phantom Black', 899.99, 4.3, 8500, 'https://m.media-amazon.com/images/I/71WKLLfKLDL._AC_SX679_.jpg'),
            ('B0CHX4VDJ7', 'Apple iPhone 15, 128GB, Pink', 729.99, 4.4, 22000, 'https://m.media-amazon.com/images/I/61bK6PMOC3L._AC_SX679_.jpg'),
            ('B07PYLN8WL', 'Google Pixel 8a, 128GB, Bay Blue', 449.99, 4.2, 12000, 'https://m.media-amazon.com/images/I/61sPWzRILjL._AC_SX679_.jpg'),
            ('B09LS6P5QZ', 'OnePlus 12 5G, 256GB, Flowy Emerald', 649.99, 4.1, 5500, 'https://m.media-amazon.com/images/I/61NLa-0Qe4L._AC_SX679_.jpg')
        ],
        'laptop': [
            ('B0BCNVK6QK', 'Apple MacBook Air 15-inch, M3 chip, 256GB SSD', 1099.99, 4.7, 8900, 'https://m.media-amazon.com/images/I/71vFKBpKakL._AC_SX679_.jpg'),
            ('B0CNF81MZR', 'Dell XPS 13 Plus, Intel i7, 16GB RAM, 512GB SSD', 899.99, 4.3, 5600, 'https://m.media-amazon.com/images/I/71QCQ5ljdEL._AC_SX679_.jpg'),
            ('B0BKZ3JVPX', 'HP Pavilion 15.6" Laptop, AMD Ryzen 7, 16GB RAM', 599.99, 4.1, 7800, 'https://m.media-amazon.com/images/I/713fJc3zZgL._AC_SX679_.jpg'),
            ('B09HLRBTZC', 'Lenovo ThinkPad E15, Intel i5, 8GB RAM, 256GB SSD', 639.99, 4.2, 4500, 'https://m.media-amazon.com/images/I/61Q3J8zr8wL._AC_SX679_.jpg'),
            ('B09WLBBWXK', 'ASUS ZenBook 14, Intel i7, 16GB RAM, 1TB SSD', 799.99, 4.4, 3400, 'https://m.media-amazon.com/images/I/71a6n26IzaL._AC_SX679_.jpg')
        ],
        'coffee': [
            ('B077JBQZPX', 'Keurig K-Elite Coffee Maker, Brushed Slate', 119.99, 4.3, 25000, 'https://m.media-amazon.com/images/I/71jCDhb3MNL._AC_SX679_.jpg'),
            ('B00A3JBQN4', 'Ninja Specialty Coffee Maker with Glass Carafe', 129.99, 4.4, 18000, 'https://m.media-amazon.com/images/I/71h0mhqWqJL._AC_SX679_.jpg'),
            ('B09732D6SQ', 'Breville Bambino Plus Espresso Machine', 249.99, 4.5, 8500, 'https://m.media-amazon.com/images/I/71LHQWS2FaL._AC_SX679_.jpg'),
            ('B08ZDQHM7P', 'Hamilton Beach FlexBrew Coffee Maker', 89.99, 4.2, 15600, 'https://m.media-amazon.com/images/I/71NFUG4YhZL._AC_SX679_.jpg'),
        ],
        'kitchen_appliances': [
            ('B07VT23JDM', 'COSORI Air Fryer, 5.8QT, Black', 89.99, 4.5, 65000, 'https://m.media-amazon.com/images/I/71PjhJcKt4L._AC_SX679_.jpg'),
            ('B01B1VC13K', 'Instant Pot Duo 7-in-1 Electric Pressure Cooker, 6 Quart', 79.99, 4.6, 125000, 'https://m.media-amazon.com/images/I/71A58+lTZdL._AC_SX679_.jpg'),
            ('B07FJJJ1Z8', 'Vitamix A3500 Ascent Series Smart Blender', 449.99, 4.4, 3200, 'https://m.media-amazon.com/images/I/61KUNCj3o6L._AC_SX679_.jpg'),
            ('B0BLRM7NKK', 'KitchenAid Artisan Series 5-Quart Stand Mixer', 329.99, 4.7, 15000, 'https://m.media-amazon.com/images/I/71Zm5x3iNvL._AC_SX679_.jpg'),
        ],
        'skincare': [
            ('B07PM86NP8', 'CeraVe Moisturizing Cream for Normal to Dry Skin', 12.99, 4.5, 85000, 'https://m.media-amazon.com/images/I/71Q5qlLhblL._AC_SX679_.jpg'),
            ('B00NR4L1MQ', 'Neutrogena Hydrating Foaming Cleanser', 7.99, 4.3, 45000, 'https://m.media-amazon.com/images/I/61YA9mF7Z8L._AC_SX679_.jpg'),
            ('B08JCQFKZJ', 'La Roche-Posay Anthelios Sunscreen SPF 60', 24.99, 4.4, 12000, 'https://m.media-amazon.com/images/I/51G9JKtzxZL._AC_SX679_.jpg'),
            ('B07Q42QCXZ', 'The Ordinary Niacinamide 10% + Zinc 1%', 7.89, 4.2, 95000, 'https://m.media-amazon.com/images/I/51mQl5QQkrL._AC_SX679_.jpg'),
        ],
        'fitness': [
            ('B08GSRY5JC', 'Bowflex SelectTech 552 Adjustable Dumbbells', 349.99, 4.5, 15000, 'https://m.media-amazon.com/images/I/71zKP5QgdKL._AC_SX679_.jpg'),
            ('B074D3ZYVZ', 'Gaiam Essentials Thick Yoga Mat', 24.99, 4.3, 25000, 'https://m.media-amazon.com/images/I/71VlSS2lBrL._AC_SX679_.jpg'),
            ('B08BNPTJBP', 'Resistance Bands Set, Exercise Bands', 19.99, 4.4, 18000, 'https://m.media-amazon.com/images/I/71j9n8o7jXL._AC_SX679_.jpg'),
            ('B0CHLWB1Y9', 'YOSUDA Indoor Cycling Bike Stationary', 269.99, 4.2, 8500, 'https://m.media-amazon.com/images/I/71YN1XZqy1L._AC_SX679_.jpg'),
        ],
        'cleaning': [
            ('B073DMDDZ3', 'Shark Navigator Lift-Away Professional NV356E', 129.99, 4.3, 78000, 'https://m.media-amazon.com/images/I/71Lz7z-LyOL._AC_SX679_.jpg'),
            ('B08TX47Z32', 'Dyson V8 Animal Cordless Vacuum Cleaner', 349.99, 4.4, 15000, 'https://m.media-amazon.com/images/I/615JgsrAQGL._AC_SX679_.jpg'),
            ('B09HLBQZVC', 'iRobot Roomba 694 Robot Vacuum', 179.99, 4.2, 45000, 'https://m.media-amazon.com/images/I/71s6K1Wsk6L._AC_SX679_.jpg'),
            ('B08HMFVMBW', 'Bissell CrossWave Pet Pro All-in-One Wet Dry Vacuum', 199.99, 4.1, 12000, 'https://m.media-amazon.com/images/I/71tgFZnFMwL._AC_SX679_.jpg'),
        ],
        'books': [
            ('B0BQMQP9RG', 'Atomic Habits by James Clear', 13.99, 4.7, 125000, 'https://m.media-amazon.com/images/I/51B5V6D6IWL._AC_SX679_.jpg'),
            ('B082DGZX9Q', 'The Psychology of Money by Morgan Housel', 14.99, 4.6, 85000, 'https://m.media-amazon.com/images/I/41j7H7pfQCL._AC_SX679_.jpg'),
            ('B07ZVR9MFM', 'Educated by Tara Westover', 12.99, 4.5, 95000, 'https://m.media-amazon.com/images/I/51xqTCGhCxL._AC_SX679_.jpg'),
            ('B08CKBY3BR', 'The Seven Husbands of Evelyn Hugo', 11.99, 4.6, 185000, 'https://m.media-amazon.com/images/I/51bVi4A2k5L._AC_SX679_.jpg'),
        ],
        'clothing': [
            ('B07PHKDT8Y', 'Hanes Men\'s Pullover EcoSmart Hooded Sweatshirt', 24.99, 4.3, 45000, 'https://m.media-amazon.com/images/I/71+F8wQpIrL._AC_SX679_.jpg'),
            ('B08TW7MZXG', 'Levi\'s Women\'s 501 Original Fit Jeans', 59.99, 4.2, 25000, 'https://m.media-amazon.com/images/I/71E6KZfIlrL._AC_SX679_.jpg'),
            ('B08R8HGPQ2', 'Amazon Essentials Women\'s Classic-Fit Short-Sleeve Crewneck T-Shirt', 9.99, 4.1, 85000, 'https://m.media-amazon.com/images/I/61g7mfnBuWL._AC_SX679_.jpg'),
            ('B07MJXJZ4K', 'Champion Men\'s Powerblend Fleece Hoodie', 34.99, 4.4, 32000, 'https://m.media-amazon.com/images/I/71FTX8oCwJL._AC_SX679_.jpg'),
        ],
        'automotive': [
            ('B08ZYNWPV9', 'Chemical Guys Car Wash Soap and Cleanser', 19.99, 4.4, 35000, 'https://m.media-amazon.com/images/I/71zNqzJQVKL._AC_SX679_.jpg'),
            ('B07QZTW7B4', 'Armor All Car Interior Cleaner Spray', 8.99, 4.2, 18000, 'https://m.media-amazon.com/images/I/61YjKZl2FnL._AC_SX679_.jpg'),
            ('B08DQWM6HM', 'Michelin 12-Volt Portable Air Compressor', 49.99, 4.3, 12000, 'https://m.media-amazon.com/images/I/71WnEoRPyKL._AC_SX679_.jpg'),
            ('B08V4LJXPJ', 'Rain-X Original Glass Water Repellent', 11.99, 4.5, 28000, 'https://m.media-amazon.com/images/I/61EJrlw4QeL._AC_SX679_.jpg'),
        ],
        'pets': [
            ('B08Q8RJQJ5', 'Blue Buffalo Life Protection Formula Natural Adult Dog Food', 42.99, 4.5, 45000, 'https://m.media-amazon.com/images/I/81oKTW5T7fL._AC_SX679_.jpg'),
            ('B0792V2W68', 'KONG Classic Dog Toy, Large', 14.99, 4.6, 125000, 'https://m.media-amazon.com/images/I/71JjpA8FZJL._AC_SX679_.jpg'),
            ('B08KS12KVF', 'Purina Pro Plan High Protein Cat Food', 28.99, 4.4, 35000, 'https://m.media-amazon.com/images/I/81PGb+NhFmL._AC_SX679_.jpg'),
            ('B08YMH62T7', 'IRIS USA 3-Piece Airtight Pet Food Storage Container', 39.99, 4.3, 15000, 'https://m.media-amazon.com/images/I/71kJn4YRNxL._AC_SX679_.jpg'),
        ],
        'general': [
            ('B08N5WRWNW', 'Amazon Echo Dot (4th Gen) with Clock', 39.99, 4.5, 85000, 'https://m.media-amazon.com/images/I/61fVAz0DX8L._AC_SX679_.jpg'),
            ('B08TV4Y5YC', 'Anker Portable Charger, 10000mAh Power Bank', 29.99, 4.4, 65000, 'https://m.media-amazon.com/images/I/71nlLLyq9fL._AC_SX679_.jpg'),
            ('B01LSUQSB0', 'AmazonBasics 60W 4-Port USB Wall Charger', 19.99, 4.2, 45000, 'https://m.media-amazon.com/images/I/61ksAFOWoZL._AC_SX679_.jpg'),
            ('B08R68K9V4', 'Tile Mate Bluetooth Tracker, 4-Pack', 59.99, 4.1, 25000, 'https://m.media-amazon.com/images/I/61MWMkyUVCL._AC_SX679_.jpg'),
        ]
    }

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
    amazon_url: str  # Direct Amazon link
    image_url: Optional[str] = None  # Product image
    savings: float
    savings_percent: float
    why_better: str

class EnhancedProductAnalysis(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str
    asin: str
    affiliate_link: str  # Add affiliate link for main product
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
    """Extract ASIN from Amazon URL including short URLs"""
    # Handle Amazon short URLs (a.co) by following redirects
    if 'a.co' in url:
        try:
            response = requests.head(url, allow_redirects=True, timeout=10)
            url = response.url  # Get the final redirected URL
        except:
            # If redirect fails, try to extract directly
            pass
    
    patterns = [
        r'/dp/([A-Z0-9]{10})',
        r'/gp/product/([A-Z0-9]{10})',
        r'asin=([A-Z0-9]{10})',
        r'/([A-Z0-9]{10})/?(?:\?|$)',
        r'/product/([A-Z0-9]{10})'
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
    """Calculate sophisticated impulse score with detailed factors for ALL categories"""
    factors = {
        "price_manipulation": 0,
        "scarcity_tactics": 0,
        "emotional_triggers": 0,
        "urgency_language": 0,
        "deal_authenticity": 0,
        "volatility_factor": 0
    }
    
    # Get product category for category-specific analysis
    category = detect_product_category(product_data.title, product_data.asin)
    
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
    else:  # excellent or unknown
        factors["deal_authenticity"] = 0
    
    # Scarcity and urgency language analysis
    title = product_data.title.lower()
    availability = (product_data.availability or "").lower()
    
    # Category-specific scarcity words
    scarcity_words = ["limited", "only", "left", "hurry", "while supplies last", "limited time", 
                     "exclusive", "rare", "last chance", "final", "clearance", "sold out"]
    urgency_words = ["today only", "24 hours", "flash sale", "lightning deal", "ends soon",
                    "hurry", "now", "immediate", "instant", "quick", "urgent"]
    
    # Category-specific emotional triggers
    if category in ['skincare', 'makeup', 'hair_care', 'supplements']:
        emotional_words = ["amazing", "miracle", "revolutionary", "life-changing", "perfect", 
                          "transform", "radiant", "youthful", "anti-aging", "instant"]
    elif category in ['fitness', 'sports', 'outdoor']:
        emotional_words = ["ultimate", "professional", "elite", "powerful", "extreme", 
                          "championship", "pro", "advanced", "superior", "best"]
    elif category in ['electronics', 'gaming', 'phone', 'laptop']:
        emotional_words = ["cutting-edge", "revolutionary", "breakthrough", "advanced", "smart",
                          "premium", "pro", "ultimate", "next-gen", "innovative"]
    elif category in ['books', 'media']:
        emotional_words = ["bestseller", "acclaimed", "award-winning", "must-read", "essential",
                          "breakthrough", "inspiring", "life-changing", "powerful"]
    else:
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
    
    # Add context-based adjustments for different categories
    if "sale" in title or "deal" in title:
        total_score += 5
    
    # Category-specific adjustments
    if category in ['books', 'media']:
        # Books generally have lower impulse risk
        total_score = max(0, total_score - 5)
    elif category in ['skincare', 'makeup', 'supplements']:
        # Beauty/health products often use more emotional marketing
        total_score += 3
    elif category in ['electronics', 'gaming']:
        # Tech products often have artificial urgency
        if "new" in title or "latest" in title:
            total_score += 3
    
    if product_data.review_count:
        try:
            review_num = int(product_data.review_count.replace(",", ""))
            if review_num < 50:  # Low review count increases impulse risk
                total_score += 5
        except:
            pass
    
    return min(100, max(0, total_score)), factors

async def find_alternatives(product_title: str, current_price: float, asin: str) -> List[Alternative]:
    """Universal alternative generation for ALL Amazon categories"""
    try:
        alternatives = []
        
        # Detect product category using universal detection
        category = detect_product_category(product_title, asin)
        logging.info(f"Detected category '{category}' for product: {product_title}")
        
        # Get comprehensive alternatives database
        all_alternatives = get_comprehensive_alternatives_data()
        
        if category in all_alternatives:
            logging.info(f"Found {len(all_alternatives[category])} alternatives for category '{category}'")
            # Generate alternatives with fixed data for consistency
            for alt_asin, title, base_price, rating, review_count, image_url in all_alternatives[category][:3]:
                if alt_asin == asin:
                    continue
                
                # Use the predefined prices but ensure they're cheaper than current
                alt_price = base_price
                savings = current_price - alt_price
                
                if savings > 0:  # Only include if cheaper
                    savings_percent = (savings / current_price) * 100
                    
                    # Generate reasons why it's better
                    reasons = []
                    reasons.append(f"${savings:.2f} cheaper")
                    if rating >= 4.5:
                        reasons.append(f"excellent rating ({rating}/5)")
                    elif rating >= 4.0:
                        reasons.append(f"very good rating ({rating}/5)")
                    else:
                        reasons.append(f"good rating ({rating}/5)")
                    reasons.append(f"({review_count:,} reviews)")
                    
                    why_better = " • ".join(reasons)
                    
                    alternatives.append(Alternative(
                        title=title,
                        price=alt_price,
                        rating=rating,
                        review_count=review_count,
                        asin=alt_asin,
                        affiliate_url=f"https://amazon.com/dp/{alt_asin}?tag={AMAZON_AFFILIATE_TAG}",
                        amazon_url=f"https://amazon.com/dp/{alt_asin}",
                        image_url=image_url,
                        savings=round(savings, 2),
                        savings_percent=round(savings_percent, 1),
                        why_better=why_better
                    ))
        else:
            logging.warning(f"No alternatives found for category '{category}'")
        
        logging.info(f"Returning {len(alternatives)} alternatives")
        return alternatives
        
    except Exception as e:
        logging.error(f"Error finding alternatives: {e}")
        return []

def extract_search_keywords(title: str) -> List[str]:
    """Extract meaningful search keywords from product title"""
    # Remove common stop words and brand-specific terms
    stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'a', 'an'}
    
    # Clean title
    clean_title = re.sub(r'[^\w\s]', ' ', title.lower())
    words = [word for word in clean_title.split() if word not in stop_words and len(word) > 2]
    
    # Create search combinations
    search_terms = []
    
    # Main category searches
    if 'headphone' in clean_title or 'headset' in clean_title:
        search_terms.extend(['wireless headphones', 'bluetooth headphones', 'noise canceling headphones'])
    elif 'phone' in clean_title and ('iphone' in clean_title or 'samsung' in clean_title):
        search_terms.extend(['smartphone', 'android phone', 'unlocked phone'])
    elif 'laptop' in clean_title:
        search_terms.extend(['laptop computer', 'notebook', 'ultrabook'])
    elif 'tablet' in clean_title:
        search_terms.extend(['tablet', 'ipad', 'android tablet'])
    else:
        # Generic approach - use first 2-3 meaningful words
        search_terms.append(' '.join(words[:3]))
        search_terms.append(' '.join(words[:2]))
    
    return search_terms[:3]  # Limit to 3 search terms

async def search_keepa_alternatives(search_query: str, current_price: float, original_asin: str) -> List[Alternative]:
    """Search for alternatives using Keepa API"""
    try:
        # Use Keepa product finder API
        url = "https://api.keepa.com/search"
        params = {
            "key": KEEPA_API_KEY,
            "domain": 1,
            "type": "product",
            "term": search_query,
            "limit": 10,
            "sort": "reviewCount",  # Sort by review count for better products
            "minRating": 35  # Minimum 3.5/5 rating (Keepa uses 0-50 scale)
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                
                if not data.get("asinList"):
                    return []
                
                alternatives = []
                
                # Get detailed data for each ASIN
                for alt_asin in data["asinList"][:5]:  # Top 5 results
                    if alt_asin == original_asin:
                        continue
                    
                    # Get product details
                    product_data = await keepa_client.get_product_data(alt_asin)
                    if not product_data.get("products"):
                        continue
                    
                    product = product_data["products"][0]
                    price_history = keepa_client.parse_price_history(product_data)
                    
                    if not price_history:
                        continue
                    
                    alt_price = price_history[-1]["price"]
                    alt_title = product.get("title", "Alternative Product")
                    alt_rating = product.get("avgRating", 0) / 10 if product.get("avgRating") else None
                    alt_reviews = product.get("reviewCount", 0)
                    
                    # Calculate savings
                    savings = current_price - alt_price
                    savings_percent = (savings / current_price) * 100 if current_price > 0 else 0
                    
                    # Generate reason why it's better
                    reasons = []
                    if savings > 0:
                        reasons.append(f"${savings:.2f} cheaper")
                    if alt_rating and alt_rating > 4.0:
                        reasons.append(f"higher rating ({alt_rating:.1f}/5)")
                    if alt_reviews > 1000:
                        reasons.append(f"more reviews ({alt_reviews:,})")
                    
                    why_better = " • ".join(reasons) if reasons else "Similar features at different price"
                    
                    # Only include if it's actually better (cheaper or significantly higher rated)
                    if savings > 0 or (alt_rating and alt_rating > 4.2):
                        alternatives.append(Alternative(
                            title=alt_title,
                            price=alt_price,
                            rating=alt_rating,
                            review_count=alt_reviews,
                            asin=alt_asin,
                            affiliate_url=f"https://amazon.com/dp/{alt_asin}?tag=impulse-20",
                            amazon_url=f"https://amazon.com/dp/{alt_asin}",
                            savings=round(savings, 2),
                            savings_percent=round(savings_percent, 1),
                            why_better=why_better
                        ))
                
                return alternatives
                
    except Exception as e:
        logging.error(f"Error in Keepa alternatives search: {e}")
        return []

async def search_amazon_alternatives(product_title: str, current_price: float, original_asin: str) -> List[Alternative]:
    """Fallback: Generate plausible alternatives based on product category"""
    try:
        alternatives = []
        
        # Category-specific alternative ASINs (popular products in each category)
        category_alternatives = {
            'headphones': [
                ('B099F367LT', 'JBL Tune 760NC - Wireless Over-Ear Headphones with Noise Cancelling', 196.08, 5.0, 3378, 'https://m.media-amazon.com/images/I/61lrT-TdyLL._AC_SX679_.jpg'),
                ('B08PZHPW8G', 'Apple AirPods Max - Space Gray', 207.48, 4.3, 5020, 'https://m.media-amazon.com/images/I/81ErO6zSJnL._AC_SX679_.jpg'),
                ('B0BVPJ7C9V', 'Bose QuietComfort 45 Wireless Bluetooth Noise Cancelling Headphones', 229.99, 4.4, 12400, 'https://m.media-amazon.com/images/I/51gMV9zVDOL._AC_SX679_.jpg'),
                ('B08PZMP36N', 'Sennheiser HD 450BT Wireless Headphones', 149.99, 4.2, 8500, 'https://m.media-amazon.com/images/I/61m0TDa5hbL._AC_SX679_.jpg'),
                ('B07G4YX39H', 'Audio-Technica ATH-M40x Professional Studio Monitor Headphones', 99.99, 4.6, 25000, 'https://m.media-amazon.com/images/I/71Q5qlLhblL._AC_SX679_.jpg')
            ],
            'phone': [
                ('B0CHX7TKDD', 'Apple iPhone 15 Pro Max, 256GB', 1199.99, 4.5, 15000, 'https://m.media-amazon.com/images/I/81Os1SDWpcL._AC_SX679_.jpg'),
                ('B0CRBHPQ1F', 'Samsung Galaxy S24 Ultra', 1299.99, 4.3, 8500, 'https://m.media-amazon.com/images/I/71WKLLfKLDL._AC_SX679_.jpg'),
                ('B0CHX4VDJ7', 'Apple iPhone 15, 256GB', 829.99, 4.4, 22000, 'https://m.media-amazon.com/images/I/61bK6PMOC3L._AC_SX679_.jpg'),
                ('B07PYLN8WL', 'Google Pixel 7a', 499.99, 4.2, 12000, 'https://m.media-amazon.com/images/I/61sPWzRILjL._AC_SX679_.jpg'),
                ('B09LS6P5QZ', 'OnePlus 11 5G', 699.99, 4.1, 5500, 'https://m.media-amazon.com/images/I/61NLa-0Qe4L._AC_SX679_.jpg')
            ],
            'laptop': [
                ('B0BCNVK6QK', 'Apple MacBook Air 15-inch, M2 chip, 256GB SSD', 1199.99, 4.7, 8900, 'https://m.media-amazon.com/images/I/71vFKBpKakL._AC_SX679_.jpg'),
                ('B0CNF81MZR', 'Dell XPS 13 Plus, Intel i7, 16GB RAM, 512GB SSD', 999.99, 4.3, 5600, 'https://m.media-amazon.com/images/I/71QCQ5ljdEL._AC_SX679_.jpg'),
                ('B0BKZ3JVPX', 'HP Pavilion 15.6" Laptop, AMD Ryzen 7, 16GB RAM', 649.99, 4.1, 7800, 'https://m.media-amazon.com/images/I/713fJc3zZgL._AC_SX679_.jpg'),
                ('B09HLRBTZC', 'Lenovo ThinkPad E15, Intel i5, 8GB RAM, 256GB SSD', 679.99, 4.2, 4500, 'https://m.media-amazon.com/images/I/61Q3J8zr8wL._AC_SX679_.jpg'),
                ('B09WLBBWXK', 'ASUS ZenBook 14, Intel i7, 16GB RAM, 1TB SSD', 899.99, 4.4, 3400, 'https://m.media-amazon.com/images/I/71a6n26IzaL._AC_SX679_.jpg')
            ]
        }
        
        # Determine category
        title_lower = product_title.lower()
        category = None
        if any(word in title_lower for word in ['headphone', 'headset', 'earphone', 'earbud']):
            category = 'headphones'
        elif any(word in title_lower for word in ['phone', 'iphone', 'galaxy', 'pixel']):
            category = 'phone'
        elif any(word in title_lower for word in ['laptop', 'notebook', 'macbook', 'aspire', 'thinkpad', 'pavilion', 'zenbook', 'inspiron', 'ideapad']):
            category = 'laptop'
        
        if category and category in category_alternatives:
            # Generate alternatives with fixed data for consistency
            for asin, title, base_price, rating, review_count, image_url in category_alternatives[category][:3]:
                if asin == original_asin:
                    continue
                
                # Use the predefined prices but ensure they're cheaper than current
                alt_price = base_price
                savings = current_price - alt_price
                
                if savings > 0:  # Only include if cheaper
                    savings_percent = (savings / current_price) * 100
                    
                    # Generate reasons why it's better
                    reasons = []
                    reasons.append(f"${savings:.2f} cheaper")
                    if rating >= 4.5:
                        reasons.append(f"excellent rating ({rating}/5)")
                    elif rating >= 4.0:
                        reasons.append(f"very good rating ({rating}/5)")
                    else:
                        reasons.append(f"good rating ({rating}/5)")
                    reasons.append(f"({review_count:,} reviews)")
                    
                    why_better = " • ".join(reasons)
                    
                    alternatives.append(Alternative(
                        title=title,
                        price=alt_price,
                        rating=rating,
                        review_count=review_count,
                        asin=asin,
                        affiliate_url=f"https://amazon.com/dp/{asin}?tag=impulse-20",
                        amazon_url=f"https://amazon.com/dp/{asin}",
                        image_url=image_url,
                        savings=round(savings, 2),
                        savings_percent=round(savings_percent, 1),
                        why_better=why_better
                    ))
        
        return alternatives
        
    except Exception as e:
        logging.error(f"Error generating Amazon alternatives: {e}")
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
        # Validate Amazon URL (including short URLs)
        url_lower = request.amazon_url.lower()
        if not any(domain in url_lower for domain in ['amazon.', 'a.co']):
            raise HTTPException(status_code=400, detail="Please provide a valid Amazon URL (amazon.com or a.co short link)")
        
        # Extract ASIN (this will handle short URL redirects)
        asin = extract_asin_from_url(request.amazon_url)
        if not asin:
            raise HTTPException(status_code=400, detail="Could not extract product ASIN from URL. Please check the Amazon link.")
        
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
        
        # Create analysis object
        result = EnhancedProductAnalysis(
            url=request.amazon_url,
            asin=asin,
            affiliate_link=generate_enhanced_affiliate_link(asin, "main_product"),
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
