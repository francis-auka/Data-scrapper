import asyncio
import re
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin
import pandas as pd

class UniversalScraper:
    """
    A generalized web scraper that automatically detects and extracts structured data
    from websites (tables, repeating lists, or articles).
    """

    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context = None

    async def _init_browser(self):
        if not self.browser:
            try:
                playwright = await async_playwright().start()
            except NotImplementedError:
                raise RuntimeError(
                    "Playwright failed to start due to asyncio event loop issues. "
                    "Please run the server using 'python run.py' instead of 'uvicorn'."
                )
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            self.context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )

    async def scrape(self, url: str, max_pages: int = 1) -> Dict[str, Any]:
        """
        Main entry point. Scrapes a URL and returns structured data.
        """
        try:
            await self._init_browser()
            page = await self.context.new_page()
            
            all_data = []
            current_url = url
            
            for page_num in range(max_pages):
                print(f"Scraping {current_url} (Page {page_num + 1})")
                
                # Load page with retries
                content = await self._load_page(page, current_url)
                if not content:
                    break
                
                soup = BeautifulSoup(content, 'html.parser')
                
                # Detect best strategy
                strategy = self._detect_strategy(soup)
                print(f"Detected strategy: {strategy}")
                
                page_data = []
                if strategy == 'table':
                    page_data = self._extract_tables(soup)
                elif strategy == 'list':
                    page_data = self._extract_repeating_items(soup)
                else:
                    page_data = self._extract_article(soup)
                
                if page_data:
                    all_data.extend(page_data)
                
                # Pagination
                if page_num < max_pages - 1:
                    next_url = await self._get_next_page(page, soup, current_url)
                    if next_url and next_url != current_url:
                        current_url = next_url
                        await asyncio.sleep(2) # Polite delay
                    else:
                        break
            
            return {
                "strategy": strategy,
                "count": len(all_data),
                "data": all_data
            }
            
        finally:
            if self.browser:
                await self.browser.close()
                self.browser = None

    async def _load_page(self, page: Page, url: str) -> Optional[str]:
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)
            await page.wait_for_load_state('networkidle', timeout=10000)
            # Scroll to bottom to trigger lazy loading
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            return await page.content()
        except Exception as e:
            print(f"Error loading {url}: {e}")
            return None

    def _detect_strategy(self, soup: BeautifulSoup) -> str:
        print("Detecting strategy...")
        # 1. Check for significant tables
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            if len(rows) > 2: # Relaxed threshold
                print(f"Found table with {len(rows)} rows. Using 'table' strategy.")
                return 'table'
        
        # 2. Check for repeating items (lists)
        # Heuristic: Find elements with same class structure appearing many times
        repeating_class = self._detect_repeating_structure(soup)
        if repeating_class:
            print(f"Found repeating structure '{repeating_class}'. Using 'list' strategy.")
            return 'list'
            
        # 3. Fallback
        print("No clear structure found. Using 'article' strategy.")
        return 'article'

    def _extract_tables(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        print("Extracting tables...")
        data = []
        tables = soup.find_all('table')
        
        # Process the largest table by row count
        if not tables:
            return []
            
        target_table = max(tables, key=lambda t: len(t.find_all('tr')))
        
        headers = []
        # Try to find headers
        thead = target_table.find('thead')
        if thead:
            headers = [th.get_text(strip=True) for th in thead.find_all(['th', 'td'])]
        
        # If no thead, check first row
        rows = target_table.find_all('tr')
        if not headers and rows:
            headers = [th.get_text(strip=True) for th in rows[0].find_all(['th', 'td'])]
            rows = rows[1:] # Skip header row
            
        # Normalize headers
        headers = [h if h else f"col_{i}" for i, h in enumerate(headers)]
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if not cells:
                continue
                
            row_data = {}
            for i, cell in enumerate(cells):
                if i < len(headers):
                    row_data[headers[i]] = cell.get_text(strip=True)
            
            if any(row_data.values()): # Skip empty rows
                data.append(row_data)
        
        print(f"Extracted {len(data)} rows from table.")
        return data

    def _detect_repeating_structure(self, soup: BeautifulSoup) -> Optional[str]:
        # Simplified detection: Look for class names that appear frequently
        classes = {}
        for elem in soup.find_all(class_=True):
            # Use only the first class to be more lenient
            if not elem.get('class'): continue
            
            cls_str = elem['class'][0]
            classes[cls_str] = classes.get(cls_str, 0) + 1
            
        # Filter for classes that appear 3+ times (relaxed from 5) and contain text
        candidates = []
        for cls, count in classes.items():
            if count >= 3:
                candidates.append(cls)
        
        # Sort by count descending
        candidates.sort(key=lambda x: classes[x], reverse=True)
        
        return candidates[0] if candidates else None

    def _extract_repeating_items(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        print("Extracting repeating items...")
        
        # 1. Identify the repeating container
        best_class = self._detect_repeating_structure(soup)
        containers = []
        
        if best_class:
            print(f"Using detected class: {best_class}")
            # Find all elements with this class
            containers = soup.find_all(class_=best_class)
        else:
            # Fallback to signature method
            print("No clear class found, trying signature method...")
            signatures = {}
            for elem in soup.find_all(['div', 'article', 'li']):
                if not elem.get_text(strip=True): continue
                sig = elem.name
                if elem.get('class'): sig += "." + ".".join(sorted(elem['class']))
                if not elem.find_all(recursive=False): continue
                signatures[sig] = signatures.get(sig, [])
                signatures[sig].append(elem)
            
            max_count = 0
            for sig, elems in signatures.items():
                if len(elems) > max_count and len(elems) > 2:
                    sample = elems[0]
                    text_children = [c for c in sample.descendants if isinstance(c, str) and c.strip()]
                    if len(text_children) > 1:
                        max_count = len(elems)
                        containers = elems

        print(f"Found {len(containers)} potential items.")
        data = []
        
        for container in containers:
            item = self._extract_item_details(container)
            # Only add if we got some meaningful text
            if item and (item.get('title') or len(item) > 1):
                data.append(item)
                
        print(f"Successfully extracted {len(data)} items.")
        return data

    def _extract_item_details(self, container: Tag) -> Dict[str, Any]:
        item = {}
        
        # Strategy: Find all child elements with class names or specific tags
        # and use them as keys
        
        # 1. Images
        img = container.find('img')
        if img and img.get('src'):
            item['image'] = img['src']
            
        # 2. Links
        link = container.find('a')
        if link and link.get('href'):
            item['link'] = link['href']
            
        # 3. Text fields
        # Iterate over children to find text
        # We limit depth to avoid grabbing too much garbage
        
        for child in container.descendants:
            if child.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                key = "title" if not item.get("title") else f"heading_{child.name}"
                item[key] = child.get_text(strip=True)
            
            elif child.name in ['p', 'span', 'div']:
                if child.get('class'):
                    # Use class name as key (simplified)
                    key = child['class'][0]
                    # Filter out common utility classes if possible, but for now just use it
                    text = child.get_text(strip=True)
                    if text and len(text) < 200: # Skip long paragraphs
                        if key not in item:
                            item[key] = text
                            
        # Cleanup keys
        clean_item = {}
        for k, v in item.items():
            if v:
                clean_item[k] = v
        
        return clean_item

    def _extract_article(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        # Extract main content
        # Heuristic: Find the element with the most text
        
        best_elem = None
        max_text_len = 0
        
        for elem in soup.find_all(['article', 'div', 'main']):
            text = elem.get_text(strip=True)
            if len(text) > max_text_len:
                max_text_len = len(text)
                best_elem = elem
                
        if best_elem:
            return [{
                "type": "article",
                "content": best_elem.get_text("\n", strip=True)[:5000], # Limit size
                "title": soup.title.string if soup.title else "No Title"
            }]
        return []

    async def _get_next_page(self, page: Page, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        # 1. Look for <link rel="next">
        link_next = soup.find('link', attrs={'rel': 'next'})
        if link_next and link_next.get('href'):
            return urljoin(current_url, link_next['href'])
            
        # 2. Look for "Next" button/link
        # We use Playwright selector to find it and click it if it's a button, 
        # or get href if it's a link.
        # For simplicity in this module, we just return the URL if we can find it.
        # If it requires a click, we might need to change the architecture to keep the page open.
        # Since we are reloading page in the loop, we prefer URL.
        
        next_texts = ['Next', 'next', '>', '»']
        for text in next_texts:
            # Find <a> with this text
            a_tag = soup.find('a', string=re.compile(text, re.I))
            if a_tag and a_tag.get('href'):
                return urljoin(current_url, a_tag['href'])
                
        return None
