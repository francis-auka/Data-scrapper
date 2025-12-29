import asyncio
import json
import re
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os


class ProductScraper:
    """
    Enhanced product-level scraper with JavaScript rendering support
    
    Features:
    - Headless browser (Playwright) for JS-rendered content
    - Auto-detect product containers and fields
    - Pagination support
    - Site-specific configurations
    """
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.path.join(
            os.path.dirname(__file__), '../config/site_configs.json'
        )
        self.configs = self._load_configs()
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
    def _load_configs(self) -> Dict:
        """Load site configurations from JSON"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load configs: {e}")
            return {"generic": self._get_generic_config()}
    
    def _get_generic_config(self) -> Dict:
        """Fallback generic configuration"""
        return {
            "name": "Generic",
            "selectors": {
                "product_container": [".product", "[itemtype*='Product']"],
                "title": ["h2", "h3", ".title"],
                "price": ["[class*='price']", ".amount"],
                "discount": ["[class*='discount']", "[class*='sale']"],
                "image": ["img"],
                "link": ["a[href]"],
                "next_page": ["a[rel='next']", ".next"]
            },
            "wait_for": ".product",
            "max_pages": 5
        }
    
    def _detect_site_config(self, url: str) -> Dict:
        """Detect which site configuration to use based on URL"""
        domain = urlparse(url).netloc.lower()
        
        # Check for specific sites
        if 'amazon' in domain:
            return self.configs.get('amazon', self.configs['generic'])
        elif 'ebay' in domain:
            return self.configs.get('ebay', self.configs['generic'])
        elif 'jumia' in domain:
            return self.configs.get('jumia', self.configs['generic'])
        elif 'shopify' in domain or any(x in domain for x in ['myshopify', '.shop']):
            return self.configs.get('shopify', self.configs['generic'])
        
        # Check page content for WooCommerce or other platforms
        # (will be done after page loads)
        
        return self.configs['generic']
    
    async def _init_browser(self):
        """Initialize Playwright browser"""
        if not self.browser:
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            
            # Create context with realistic settings
            context = await self.browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080},
                locale='en-US'
            )
            
            self.page = await context.new_page()
    
    async def _load_page(self, url: str, wait_selector: str = None, timeout: int = 30000):
        """Load page and wait for content"""
        try:
            await self.page.goto(url, wait_until='domcontentloaded', timeout=timeout)
            
            # Wait for dynamic content
            if wait_selector:
                try:
                    await self.page.wait_for_selector(wait_selector, timeout=10000)
                except:
                    pass  # Continue even if wait fails
            
            # Additional wait for JS rendering
            await asyncio.sleep(2)
            
            return await self.page.content()
        except Exception as e:
            print(f"Error loading page {url}: {e}")
            return None
    
    def _try_selectors(self, soup, selectors: List[str], container=None):
        """Try multiple selectors and return first match"""
        search_scope = container if container else soup
        
        for selector in selectors:
            try:
                result = search_scope.select_one(selector)
                if result:
                    return result
            except:
                continue
        return None
    
    def _extract_price(self, text: str) -> Optional[float]:
        """Extract numeric price from text"""
        if not text:
            return None
        
        # Remove currency symbols and extract number
        price_match = re.search(r'[\d,]+\.?\d*', text.replace(',', ''))
        if price_match:
            try:
                return float(price_match.group())
            except:
                pass
        return None
    
    def _extract_product_data(self, container, config: Dict, base_url: str) -> Dict[str, Any]:
        """Extract product data from a container element"""
        soup = BeautifulSoup(str(container), 'html.parser')
        selectors = config['selectors']
        
        product = {
            'title': None,
            'price': None,
            'discount': None,
            'url': None,
            'image': None
        }
        
        # Extract title
        title_elem = self._try_selectors(soup, selectors.get('title', []))
        if title_elem:
            product['title'] = title_elem.get_text(strip=True)
        
        # Extract price
        price_elem = self._try_selectors(soup, selectors.get('price', []))
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            product['price'] = self._extract_price(price_text)
        
        # Extract discount
        discount_elem = self._try_selectors(soup, selectors.get('discount', []))
        if discount_elem:
            product['discount'] = discount_elem.get_text(strip=True)
        
        # Extract URL
        link_elem = self._try_selectors(soup, selectors.get('link', []))
        if link_elem and link_elem.get('href'):
            product['url'] = urljoin(base_url, link_elem['href'])
        
        # Extract image
        image_elem = self._try_selectors(soup, selectors.get('image', []))
        if image_elem:
            image_url = image_elem.get('src') or image_elem.get('data-src')
            if image_url:
                product['image'] = urljoin(base_url, image_url)
        
        return product
    
    async def _get_next_page_url(self, current_url: str, config: Dict) -> Optional[str]:
        """Detect and return next page URL"""
        try:
            next_selectors = config['selectors'].get('next_page', [])
            
            for selector in next_selectors:
                next_elem = await self.page.query_selector(selector)
                if next_elem:
                    href = await next_elem.get_attribute('href')
                    if href:
                        return urljoin(current_url, href)
        except Exception as e:
            print(f"Error finding next page: {e}")
        
        return None
    
    async def scrape_products(self, url: str, max_pages: int = None) -> List[Dict[str, Any]]:
        """
        Main scraping function - extracts products from URL with pagination
        
        Args:
            url: Starting URL to scrape
            max_pages: Maximum pages to scrape (None = use config default)
            
        Returns:
            List of product dictionaries with title, price, discount, url, image
        """
        all_products = []
        current_url = url
        page_count = 0
        
        # Detect site configuration
        config = self._detect_site_config(url)
        max_pages = max_pages or config.get('max_pages', 5)
        
        try:
            # Initialize browser
            await self._init_browser()
            
            while current_url and page_count < max_pages:
                print(f"Scraping page {page_count + 1}: {current_url}")
                print(f"Using config: {config['name']}")
                
                # Load page
                html = await self._load_page(
                    current_url,
                    wait_selector=config.get('wait_for')
                )
                
                if not html:
                    print("Failed to load page content")
                    break
                
                # Parse HTML
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find product containers
                containers = []
                for selector in config['selectors'].get('product_container', []):
                    try:
                        print(f"Trying container selector: {selector}")
                        found = soup.select(selector)
                        if found:
                            print(f"Found {len(found)} containers with selector: {selector}")
                            containers = found
                            break
                    except Exception as e:
                        print(f"Selector error {selector}: {e}")
                        continue
                
                if not containers:
                    print(f"No products found on page {page_count + 1}")
                    # Debug: print some HTML to see what we got
                    print(f"Page title: {soup.title.string if soup.title else 'No title'}")
                    print(f"HTML snippet: {html[:500]}...")
                    break
                
                print(f"Found {len(containers)} products on page {page_count + 1}")
                
                # Extract data from each product
                products_on_page = 0
                for i, container in enumerate(containers):
                    product_data = self._extract_product_data(container, config, current_url)
                    
                    # Debug first product extraction
                    if i == 0:
                        print(f"First product extraction attempt: {product_data}")
                        print(f"Container HTML snippet: {str(container)[:200]}...")
                    
                    # Only add if we got meaningful data
                    if product_data.get('title') or product_data.get('price'):
                        all_products.append(product_data)
                        products_on_page += 1
                
                print(f"Successfully extracted {products_on_page} products from page {page_count + 1}")
                page_count += 1
                
                # Find next page
                if page_count < max_pages:
                    next_url = await self._get_next_page_url(current_url, config)
                    if next_url and next_url != current_url:
                        current_url = next_url
                        await asyncio.sleep(2)  # Rate limiting
                    else:
                        break
                else:
                    break
            
        finally:
            # Clean up
            if self.browser:
                await self.browser.close()
                self.browser = None
                self.page = None
        
        print(f"Total products scraped: {len(all_products)}")
        return all_products
    
    async def scrape_with_auto_detect(self, url: str, max_pages: int = 3) -> List[Dict[str, Any]]:
        """
        Scrape using auto-detection if no config matches
        """
        from app.services.selector_detector import SelectorDetector
        
        try:
            await self._init_browser()
            
            # Load first page
            html = await self._load_page(url)
            if not html:
                return []
            
            # Auto-detect selectors
            detector = SelectorDetector(html)
            detected = detector.auto_detect_selectors()
            
            if not detected.get('product_container'):
                print("Could not auto-detect products")
                return []
            
            # Create temporary config
            temp_config = {
                "selectors": detected,
                "max_pages": max_pages
            }
            
            print(f"Auto-detected selectors: {detected}")
            
            # Use detected config to scrape
            return await self.scrape_products(url, max_pages)
            
        finally:
            if self.browser:
                await self.browser.close()
                self.browser = None
