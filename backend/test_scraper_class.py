import asyncio
import sys
import os
import json

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'app'))

# Fix for Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from app.services.product_scraper import ProductScraper

async def test_scraper():
    print("Testing ProductScraper...")
    scraper = ProductScraper()
    
    url = "https://www.jumia.co.ke/catalog/?q=samsung+a17"
    print(f"URL: {url}")
    
    # Check config detection
    config = scraper._detect_site_config(url)
    print(f"Detected config: {config.get('name')}")
    
    if config.get('name') != 'Jumia':
        print("ERROR: Jumia config not detected!")
        return

    print("Jumia config detected successfully.")
    
    # Run scrape
    print("\nStarting scrape (max_pages=1)...")
    try:
        products = await scraper.scrape_products(url, max_pages=1)
        print(f"\nScrape finished. Found {len(products)} products.")
        if products:
            print(f"First product title: {products[0].get('title')}")
            print(f"First product price: {products[0].get('price')}")
    except Exception as e:
        print(f"Scrape failed: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(test_scraper())
    except Exception as e:
        print(f"Main execution error: {e}")
