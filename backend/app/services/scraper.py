import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import List, Optional, Dict, Any
from app.core.task_manager import task_manager
from app.parsers.generic import GenericParser
from app.parsers.linkedin import LinkedInParser
from app.parsers.amazon import AmazonParser

async def scrape_urls(task_id: str, urls: List[str], keywords: Optional[List[str]] = None, site_filter: Optional[str] = None):
    task_manager.update_task(task_id, status="running", progress=0)
    results = []
    total = len(urls)
    
    async with aiohttp.ClientSession() as session:
        for i, url in enumerate(urls):
            try:
                # Select parser based on URL
                if "linkedin.com" in url:
                    parser = LinkedInParser()
                elif "amazon.com" in url or "amazon." in url:
                    parser = AmazonParser()
                else:
                    parser = GenericParser()
                
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        html = await response.text()
                        data = parser.parse(html, url)
                        results.append(data)
                    else:
                        results.append({"url": url, "error": f"HTTP {response.status}"})
            except Exception as e:
                results.append({"url": url, "error": str(e)})
            
            progress = int(((i + 1) / total) * 100)
            task_manager.update_task(task_id, progress=progress)
            await asyncio.sleep(1) # Rate limiting
    
    task_manager.update_task(task_id, status="completed", progress=100, result=results)

async def search_and_scrape(task_id: str, keywords: List[str], site_filter: Optional[str] = None):
    # Simplified search logic for MVP
    # In a real app, we'd use a search engine API
    task_manager.update_task(task_id, status="running", progress=10)
    # Mock search results
    urls = [f"https://www.google.com/search?q={k}" for k in keywords]
    await scrape_urls(task_id, urls)
