from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ScrapeRequest(BaseModel):
    urls: List[str]
    keywords: Optional[List[str]] = None
    site_filter: Optional[str] = None

class ProcessRequest(BaseModel):
    data_id: str
    operations: List[Dict[str, Any]]

class TaskResponse(BaseModel):
    id: str
    type: str
    status: str
    progress: int
    result: Optional[Any] = None
    error: Optional[str] = None

class DataIdRequest(BaseModel):
    data_id: str

class ProductScrapeRequest(BaseModel):
    urls: List[str]
    max_pages: Optional[int] = 3
    auto_detect: Optional[bool] = False


