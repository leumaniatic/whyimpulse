from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import asyncio
import re
import json

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

# OpenAI API Key
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

# Define Models
class ProductAnalysisRequest(BaseModel):
    amazon_url: str

class ProductData(BaseModel):
    title: str
    price: Optional[str] = None
    image_url: Optional[str] = None
    rating: Optional[str] = None
    review_count: Optional[str] = None
    availability: Optional[str] = None

class ProductAnalysis(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    url: str
    product_data: ProductData
    verdict: str
    pros: List[str]
    cons: List[str]
    impulse_score: int
    recommendation: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Amazon scraper function
def extract_amazon_product_data(url: str) -> ProductData:
    """Extract product data from Amazon URL"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
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
            availability=availability
        )
        
    except Exception as e:
        logging.error(f"Error scraping Amazon: {e}")
        # Return basic data if scraping fails
        return ProductData(
            title="Unable to extract product data",
            price=None,
            image_url=None,
            rating=None,
            review_count=None,
            availability=None
        )

async def analyze_with_gpt4(product_data: ProductData, url: str) -> dict:
    """Analyze product data using GPT-4"""
    try:
        # Install emergentintegrations if not available
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
        except ImportError:
            import subprocess
            subprocess.check_call([
                "pip", "install", "emergentintegrations", 
                "--extra-index-url", "https://d33sy5i8bnduwe.cloudfront.net/simple/"
            ])
            from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        # Initialize GPT-4 chat
        chat = LlmChat(
            api_key=OPENAI_API_KEY,
            session_id=f"product-analysis-{uuid.uuid4()}",
            system_message="""You are an expert product analyst specializing in smart purchasing decisions. 
            Analyze product data and provide detailed buying recommendations.
            
            Return your analysis in this EXACT JSON format:
            {
                "verdict": "BUY/WAIT/SKIP with brief reason",
                "pros": ["pro1", "pro2", "pro3"],
                "cons": ["con1", "con2", "con3"], 
                "impulse_score": 1-100,
                "recommendation": "Detailed recommendation paragraph"
            }
            
            Impulse Score Guide:
            - 90-100: Impulse buy (urgent sale words, FOMO tactics)
            - 70-89: High impulse (limited time, trending)
            - 50-69: Medium impulse (good product, consider waiting)
            - 30-49: Low impulse (research more, compare alternatives)
            - 1-29: Skip impulse (poor value, wait for better price)"""
        ).with_model("openai", "gpt-4o")
        
        # Create analysis prompt
        analysis_prompt = f"""
        Analyze this Amazon product for a smart buying decision:
        
        Product: {product_data.title}
        Price: {product_data.price or 'Not available'}
        Rating: {product_data.rating or 'Not available'} 
        Reviews: {product_data.review_count or 'Not available'}
        Availability: {product_data.availability or 'Not available'}
        URL: {url}
        
        Provide verdict (BUY/WAIT/SKIP), pros, cons, impulse score (1-100), and recommendation.
        Focus on value, timing, and whether this seems like an impulse purchase.
        """
        
        user_message = UserMessage(text=analysis_prompt)
        response = await chat.send_message(user_message)
        
        # Parse JSON response
        try:
            # Extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end != 0:
                json_str = response[json_start:json_end]
                analysis = json.loads(json_str)
            else:
                # Fallback parsing
                analysis = {
                    "verdict": "Unable to analyze - check product URL",
                    "pros": ["Product data available"],
                    "cons": ["Limited analysis due to parsing error"],
                    "impulse_score": 50,
                    "recommendation": response[:500] + "..." if len(response) > 500 else response
                }
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            analysis = {
                "verdict": "Analysis completed with limited data",
                "pros": ["Product information extracted"],
                "cons": ["Detailed analysis unavailable"],
                "impulse_score": 50,
                "recommendation": response[:500] + "..." if len(response) > 500 else response
            }
            
        return analysis
        
    except Exception as e:
        logging.error(f"Error with GPT-4 analysis: {e}")
        return {
            "verdict": "WAIT - Analysis temporarily unavailable",
            "pros": ["Product URL provided"],
            "cons": ["Unable to perform detailed analysis"],
            "impulse_score": 50,
            "recommendation": "Unable to analyze product at this time. Please try again later or verify the Amazon URL is correct."
        }

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Impulse Saver API is running!"}

@api_router.post("/analyze", response_model=ProductAnalysis)
async def analyze_product(request: ProductAnalysisRequest):
    """Analyze Amazon product and provide buying recommendation"""
    try:
        # Validate Amazon URL
        if 'amazon.' not in request.amazon_url.lower():
            raise HTTPException(status_code=400, detail="Please provide a valid Amazon URL")
        
        # Extract product data
        product_data = extract_amazon_product_data(request.amazon_url)
        
        # Analyze with GPT-4
        analysis = await analyze_with_gpt4(product_data, request.amazon_url)
        
        # Create analysis object
        result = ProductAnalysis(
            url=request.amazon_url,
            product_data=product_data,
            verdict=analysis["verdict"],
            pros=analysis["pros"],
            cons=analysis["cons"],
            impulse_score=analysis["impulse_score"],
            recommendation=analysis["recommendation"]
        )
        
        # Save to database
        await db.product_analyses.insert_one(result.dict())
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error analyzing product: {e}")
        raise HTTPException(status_code=500, detail="Error analyzing product. Please try again.")

@api_router.get("/recent-analyses", response_model=List[ProductAnalysis])
async def get_recent_analyses(limit: int = 10):
    """Get recent product analyses"""
    try:
        analyses = await db.product_analyses.find().sort("timestamp", -1).limit(limit).to_list(limit)
        return [ProductAnalysis(**analysis) for analysis in analyses]
    except Exception as e:
        logging.error(f"Error fetching analyses: {e}")
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
