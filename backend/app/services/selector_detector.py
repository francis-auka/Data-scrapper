import re
from typing import List, Dict, Optional
from bs4 import BeautifulSoup


class SelectorDetector:
    """Auto-detect product containers and extract selectors from HTML"""
    
    def __init__(self, html: str):
        self.soup = BeautifulSoup(html, 'html.parser')
        
    def detect_product_containers(self) -> List[str]:
        """
        Detect likely product container selectors using heuristics
        
        Returns list of CSS selectors that likely contain products
        """
        candidates = []
        
        # 1. Look for schema.org Product markup
        schema_products = self.soup.find_all(attrs={'itemtype': re.compile(r'Product', re.I)})
        if schema_products:
            for elem in schema_products:
                if elem.get('class'):
                    candidates.append('.' + '.'.join(elem['class']))
                if elem.name:
                    candidates.append(f"{elem.name}[itemtype*='Product']")
        
        # 2. Look for common product class patterns
        product_patterns = [
            'product-card', 'product-item', 'product-box', 'product-tile',
            'grid-product', 'list-product', 'search-result', 's-result-item'
        ]
        
        for pattern in product_patterns:
            elements = self.soup.find_all(class_=re.compile(pattern, re.I))
            if elements:
                # Get the most specific class
                for elem in elements[:1]:  # Check first element
                    if elem.get('class'):
                        candidates.append('.' + '.'.join(elem['class']))
        
        # 3. Look for repeated structures with prices
        # Find all elements with price-like content
        price_elements = self.soup.find_all(text=re.compile(r'[$€£¥]\s*\d+'))
        
        if price_elements:
            # Find their common parent containers
            containers = {}
            for price in price_elements:
                parent = price.find_parent(['div', 'article', 'li', 'section'])
                if parent:
                    parent_sig = self._get_element_signature(parent)
                    containers[parent_sig] = containers.get(parent_sig, 0) + 1
            
            # If we found repeated containers (likely products)
            for sig, count in containers.items():
                if count >= 3:  # At least 3 similar containers
                    candidates.append(sig)
        
        return list(set(candidates))  # Remove duplicates
    
    def detect_price_selector(self, container) -> Optional[str]:
        """Detect price selector within a container"""
        # Look for price patterns
        price_patterns = [
            r'[$€£¥]\s*\d+',
            r'\d+[.,]\d{2}\s*[$€£¥]'
        ]
        
        for pattern in price_patterns:
            price_elem = container.find(text=re.compile(pattern))
            if price_elem:
                parent = price_elem.find_parent(['span', 'div', 'p'])
                if parent and parent.get('class'):
                    return '.' + '.'.join(parent['class'])
        
        # Common price class patterns
        price_classes = ['price', 'amount', 'cost', 'rate']
        for cls in price_classes:
            elem = container.find(class_=re.compile(cls, re.I))
            if elem and elem.get('class'):
                return '.' + '.'.join(elem['class'])
        
        return None
    
    def detect_title_selector(self, container) -> Optional[str]:
        """Detect title selector within a container"""
        # Look for headings first
        for heading in ['h1', 'h2', 'h3', 'h4']:
            title = container.find(heading)
            if title:
                if title.get('class'):
                    return f"{heading}." + '.'.join(title['class'])
                return heading
        
        # Look for common title classes
        title_classes = ['title', 'name', 'heading', 'product-title']
        for cls in title_classes:
            elem = container.find(class_=re.compile(cls, re.I))
            if elem and elem.get('class'):
                return '.' + '.'.join(elem['class'])
        
        return None
    
    def detect_image_selector(self, container) -> Optional[str]:
        """Detect image selector within a container"""
        img = container.find('img')
        if img:
            if img.get('class'):
                return 'img.' + '.'.join(img['class'])
            return 'img'
        return None
    
    def detect_link_selector(self, container) -> Optional[str]:
        """Detect product link selector"""
        # Look for links with product-related hrefs
        link = container.find('a', href=re.compile(r'product|item|/p/', re.I))
        if link:
            if link.get('class'):
                return 'a.' + '.'.join(link['class'])
            return 'a[href]'
        
        # Just get first link
        link = container.find('a')
        if link:
            return 'a[href]'
        
        return None
    
    def _get_element_signature(self, elem) -> str:
        """Get a CSS selector signature for an element"""
        if elem.get('class'):
            return '.' + '.'.join(elem['class'])
        elif elem.get('id'):
            return f"#{elem['id']}"
        else:
            return elem.name
    
    def auto_detect_selectors(self) -> Dict[str, List[str]]:
        """
        Auto-detect all selectors for product scraping
        
        Returns dict with detected selectors
        """
        containers = self.detect_product_containers()
        
        if not containers:
            return {}
        
        # Use first container to detect field selectors
        container_selector = containers[0]
        sample_container = self.soup.select_one(container_selector)
        
        if not sample_container:
            return {}
        
        detected = {
            "product_container": containers,
            "title": [],
            "price": [],
            "image": [],
            "link": []
        }
        
        # Detect field selectors
        title_sel = self.detect_title_selector(sample_container)
        if title_sel:
            detected["title"].append(title_sel)
        
        price_sel = self.detect_price_selector(sample_container)
        if price_sel:
            detected["price"].append(price_sel)
        
        image_sel = self.detect_image_selector(sample_container)
        if image_sel:
            detected["image"].append(image_sel)
        
        link_sel = self.detect_link_selector(sample_container)
        if link_sel:
            detected["link"].append(link_sel)
        
        return detected
