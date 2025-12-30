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
        strategy = "none"
        all_data = []
        print(f"DEBUG: Starting scrape for {url}, strategy initialized to {strategy}")
        
        try:
            await self._init_browser()
            page = await self.context.new_page()
            
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
            # Use a more generous timeout and wait for load state
            print(f"DEBUG: Loading page {url}...")
            await page.goto(url, wait_until='load', timeout=60000)
            
            # Network idle is often problematic on sites like Jumia, so we make it optional
            try:
                await page.wait_for_load_state('networkidle', timeout=5000)
            except Exception:
                print(f"DEBUG: Network didn't go idle for {url}, proceeding anyway")
            
            # Scroll to bottom to trigger lazy loading
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            
            content = await page.content()
            print(f"DEBUG: Page loaded successfully, content length: {len(content)}")
            return content
        except Exception as e:
            print(f"DEBUG: Error loading {url}: {str(e)}")
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
        """
        Detects the most likely class for repeating items (like product cards).
        """
        candidates = {}
        price_pattern = re.compile(r'(KSh|[\$£€]|Rs\.?|Price|[\d,]+\.\d{2})', re.I)
        
        # We look for elements that have some content (links or images)
        for elem in soup.find_all(['div', 'article', 'li', 'a'], class_=True):
            if not elem.get('class'): continue
            
            # Heuristic: Must have at least one link or image to be a "card"
            if not (elem.find('a') or elem.find('img')):
                continue
                
            # Heuristic: Must have some text
            text = elem.get_text(" ", strip=True)
            if len(text) < 15: # Increased from 10
                continue
                
            cls_str = elem['class'][0]
            if cls_str not in candidates:
                candidates[cls_str] = {
                    'count': 0,
                    'total_text_len': 0,
                    'has_img': 0,
                    'has_link': 0,
                    'has_price': 0,
                    'tag_diversity': set()
                }
            
            candidates[cls_str]['count'] += 1
            candidates[cls_str]['total_text_len'] += len(text)
            if elem.find('img'): candidates[cls_str]['has_img'] += 1
            if elem.find('a'): candidates[cls_str]['has_link'] += 1
            if price_pattern.search(text): candidates[cls_str]['has_price'] += 1
            
            # Count unique tag types inside
            for child in elem.find_all(True):
                candidates[cls_str]['tag_diversity'].add(child.name)
            
        # Score the candidates
        scored = []
        for cls, stats in candidates.items():
            count = stats['count']
            
            # We prefer counts between 5 and 100 (typical for a page)
            if count < 3 or count > 200:
                continue
                
            # Score based on content richness
            avg_text = stats['total_text_len'] / count
            img_ratio = stats['has_img'] / count
            link_ratio = stats['has_link'] / count
            price_ratio = stats['has_price'] / count
            diversity = len(stats['tag_diversity'])
            
            # Base score is count
            score = count
            
            # Multipliers for "Product-like" features
            score *= (1 + img_ratio)
            score *= (1 + link_ratio)
            score *= (1 + price_ratio * 5) # Heavy weight on prices
            score *= (1 + (diversity / 10)) # Weight on tag diversity
            
            if avg_text > 40: score *= 1.5 # Product titles + prices are usually longer than nav links
            
            scored.append((cls, score, count, price_ratio))
            
        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        
        if scored:
            print(f"DEBUG: Top candidates: {scored[:3]}")
            return scored[0][0]
            
        return None

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
        
        for i, container in enumerate(containers):
            item = self._extract_item_details(container)
            
            # Debug the first 3 items to see what's being found
            if i < 3:
                print(f"DEBUG: Item {i} raw extraction: {item}")
                
            # Only add if we got some meaningful text
            # We check if we have at least 2 fields or a title
            if item and (item.get('title') or len(item) >= 2):
                data.append(item)
                
        print(f"Successfully extracted {len(data)} items.")
        return data

    def _extract_item_details(self, container: Tag) -> Dict[str, Any]:
        item = {}
        price_pattern = re.compile(r'(KSh|[\$£€]|Rs\.?|Price|[\d,]+\.\d{2})', re.I)
        
        # 1. Images
        img = container.find('img')
        if img:
            img_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if img_url:
                item['image'] = img_url
            
        # 2. Links
        link = container.find('a')
        if link and link.get('href'):
            item['link'] = link['href']
            
        # 3. Text fields
        text_elements = container.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'span', 'div', 'b', 'strong'])
        
        all_texts = []
        for elem in text_elements:
            if elem.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'span', 'div', 'b', 'strong']):
                continue
                
            text = elem.get_text(strip=True)
            if not text or len(text) > 300:
                continue
            all_texts.append((elem, text))
            
        # Try to identify specific fields
        for elem, text in all_texts:
            # Price detection
            if price_pattern.search(text) and len(text) < 30:
                key = "price" if "price" not in item else f"price_{len(item)}"
                item[key] = text
                continue
                
            # Title detection (usually the longest text or a heading)
            if elem.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'] or len(text) > 30:
                if "title" not in item or len(text) > len(item.get("title", "")):
                    item["title"] = text
                continue
            
            # Generic fields
            if elem.get('class'):
                cls = elem['class'][0]
                if cls not in ['text', 'content', 'inner', 'name', 'price']:
                    item[cls] = text
                else:
                    item[f"field_{len(item)}"] = text
            else:
                item[f"field_{len(item)}"] = text
                            
        clean_item = {}
        for k, v in item.items():
            if v and len(str(v)) > 1:
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
