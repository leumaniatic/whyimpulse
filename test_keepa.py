#!/usr/bin/env python3

import asyncio
import aiohttp
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv('/app/backend/.env')

KEEPA_API_KEY = os.environ.get('KEEPA_API_KEY')

async def test_keepa_api():
    """Test Keepa API directly"""
    print(f"Testing Keepa API with key: {KEEPA_API_KEY[:10]}...")
    
    # Test with a popular product ASIN
    asin = "B08N5WRWNW"  # Example ASIN
    domain = 1  # US domain
    
    url = "https://api.keepa.com/product"
    params = {
        "key": KEEPA_API_KEY,
        "domain": domain,
        "asin": asin,
        "stats": 1,
        "history": 1,
        "offers": 20
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            print(f"Making request to: {url}")
            print(f"Parameters: {params}")
            
            async with session.get(url, params=params) as response:
                print(f"Response status: {response.status}")
                print(f"Response headers: {dict(response.headers)}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"Response data keys: {list(data.keys())}")
                    
                    if 'products' in data and data['products']:
                        product = data['products'][0]
                        print(f"Product keys: {list(product.keys())}")
                        print(f"Product title: {product.get('title', 'No title')}")
                        print(f"CSV data length: {len(product.get('csv', []))}")
                        print(f"First 10 CSV values: {product.get('csv', [])[:10]}")
                        
                        return data
                    else:
                        print("No products found in response")
                        return {}
                else:
                    error_text = await response.text()
                    print(f"Error response: {error_text}")
                    return {}
                    
    except Exception as e:
        print(f"Exception during API call: {e}")
        return {}

async def test_keepa_search():
    """Test Keepa search functionality"""
    print("\nTesting Keepa search...")
    
    url = "https://api.keepa.com/search"
    params = {
        "key": KEEPA_API_KEY,
        "domain": 1,
        "type": "product",
        "term": "wireless headphones",
        "limit": 5
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                print(f"Search response status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"Search response keys: {list(data.keys())}")
                    print(f"ASINs found: {data.get('asinList', [])}")
                    return data
                else:
                    error_text = await response.text()
                    print(f"Search error: {error_text}")
                    return {}
                    
    except Exception as e:
        print(f"Search exception: {e}")
        return {}

if __name__ == "__main__":
    asyncio.run(test_keepa_api())
    asyncio.run(test_keepa_search())