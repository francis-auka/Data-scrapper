from bs4 import BeautifulSoup
from app.parsers.base import BaseParser
from typing import Dict, Any

class GenericParser(BaseParser):
    def parse(self, html: str, url: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, 'html.parser')
        return {
            "url": url,
            "title": soup.title.string if soup.title else "No Title",
            "description": soup.find("meta", attrs={"name": "description"})["content"] if soup.find("meta", attrs={"name": "description"}) else "No Description",
            "h1": [h.get_text(strip=True) for h in soup.find_all("h1")],
            "links": len(soup.find_all("a")),
            "images": len(soup.find_all("img"))
        }
