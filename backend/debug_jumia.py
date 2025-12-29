import asyncio
from playwright.async_api import async_playwright
import sys

# Fix for Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

async def debug_jumia():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        url = "https://www.jumia.co.ke/catalog/?q=samsung+a17"
        print(f"Loading {url}...")
        
        await page.goto(url, timeout=60000)
        await page.wait_for_load_state("networkidle")
        
        # Get content
        content = await page.content()
        
        # Save to file for inspection
        with open("jumia_debug.html", "w", encoding="utf-8") as f:
            f.write(content)
            
        print("Saved HTML to jumia_debug.html")
        
        # Try to find products with current selectors
        print("\nTesting selectors:")
        
        selectors = [
            "article.prd",
            "a.core", 
            "article.c-prd",
            ".core",
            "[data-id]"
        ]
        
        for sel in selectors:
            count = await page.locator(sel).count()
            print(f"Selector '{sel}': found {count} elements")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_jumia())
