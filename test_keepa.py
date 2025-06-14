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
    
    # Test with popular product ASINs
    domain = 1  # US domain
    test_asins = [
        "B08N5WRWNW",  # Original ASIN
        "B0863TXGM3",  # Sony WH-1000XM4 Headphones  
        "B09G9HD6PD",  # iPhone 13
        "B08KTZ8249",  # Kindle Paperwhite
        "B07FZ8S74R",  # Echo Dot
    ]
    
    for asin in test_asins:
        print(f"\n=== Testing ASIN: {asin} ===")
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
                    
                    if response.status == 200:
                        data = await response.json()
                        print(f"Response data keys: {list(data.keys())}")
                        
                        if 'products' in data and data['products']:
                            product = data['products'][0]
                            print(f"Product title: {product.get('title', 'No title')}")
                            print(f"CSV data length: {len(product.get('csv', []))}")
                            
                            # Check if we have valid CSV data
                            csv_data = product.get('csv', [])
                            valid_data = [x for x in csv_data if x is not None and x != -1]
                            print(f"Valid CSV data points: {len(valid_data)}")
                            
                            if valid_data:
                                print(f"Sample valid data: {valid_data[:10]}")
                                return data  # Return first successful result
                            else:
                                print("No valid price data found")
                        else:
                            print("No products found in response")
                    else:
                        error_text = await response.text()
                        print(f"Error response: {error_text}")
                        
        except Exception as e:
            print(f"Exception during API call: {e}")
    
    return {}  # Return empty if no valid data found

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