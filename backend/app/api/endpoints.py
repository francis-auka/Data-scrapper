from fastapi import APIRouter, BackgroundTasks, UploadFile, File, HTTPException, Query
from typing import List, Optional
from app.core.task_manager import task_manager
from app.services.scraper import scrape_urls
from app.services.processor import process_data
import pandas as pd
import io
import json

router = APIRouter()

from app.models.schemas import ScrapeRequest, ProcessRequest

@router.post("/scrape")
async def start_scrape(
    background_tasks: BackgroundTasks,
    request: ScrapeRequest
):
    task_id = task_manager.create_task("scrape", {"urls": request.urls, "keywords": request.keywords, "site_filter": request.site_filter})
    background_tasks.add_task(scrape_urls, task_id, request.urls, request.keywords, request.site_filter)
    return {"task_id": task_id}

@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.get("/tasks")
async def list_tasks():
    return task_manager.list_tasks()

@router.post("/upload")
async def upload_file(file: UploadFile = File(...), preview_rows: int = Query(100)):
    content = await file.read()
    filename = file.filename
    
    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        elif filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(content))
        elif filename.endswith('.json'):
            df = pd.read_json(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
        
        data_id = task_manager.create_task("upload", {"filename": filename})
        task_manager.update_task(data_id, status="completed", result=df.to_dict(orient='records'))
        
        from app.services.processor import get_column_info
        return {
            "data_id": data_id, 
            "preview": df.head(preview_rows).to_dict(orient='records'), 
            "columns": get_column_info(df),
            "total_rows": len(df)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process")
async def process_dataset(
    request: ProcessRequest,
    preview_rows: int = Query(100)
):
    task = task_manager.get_task(request.data_id)
    if not task or not task.get("result"):
        raise HTTPException(status_code=404, detail="Data not found")
    
    df = pd.DataFrame(task["result"])
    processed_df = process_data(df, request.operations)
    
    new_data_id = task_manager.create_task("process", {"parent_id": request.data_id, "operations": request.operations})
    task_manager.update_task(new_data_id, status="completed", result=processed_df.to_dict(orient='records'))
    
    from app.services.processor import get_column_info
    return {
        "data_id": new_data_id, 
        "preview": processed_df.head(preview_rows).to_dict(orient='records'),
        "columns": get_column_info(processed_df),
        "total_rows": len(processed_df)
    }

@router.get("/export/{data_id}")
async def export_data(data_id: str, format: str = "csv"):
    task = task_manager.get_task(data_id)
    if not task or not task.get("result"):
        raise HTTPException(status_code=404, detail="Data not found")
    
    df = pd.DataFrame(task["result"])
    
    if format == "csv":
        output = io.StringIO()
        df.to_csv(output, index=False)
        return {"content": output.getvalue(), "filename": f"export_{data_id}.csv", "mime_type": "text/csv"}
    elif format == "json":
        return {"content": df.to_json(orient='records'), "filename": f"export_{data_id}.json", "mime_type": "application/json"}
    else:
        raise HTTPException(status_code=400, detail="Unsupported export format")

@router.post("/auto-clean")
async def auto_clean_dataset(request: dict):
    """
    Automatically clean the dataset and return cleaned data with detailed report.
    
    Request body:
    - data_id: ID of the dataset to clean
    
    Returns:
    - cleaned_data_id: New data ID for cleaned dataset
    - cleaning_report: Detailed report of all changes made
    - preview: First 100 rows of cleaned data
    - columns: Updated column information
    - total_rows: Row count after cleaning
    """
    from app.models.schemas import DataIdRequest
    
    # Validate request
    if isinstance(request, dict):
        data_id = request.get("data_id")
    else:
        data_id = request.data_id
        
    if not data_id:
        raise HTTPException(status_code=400, detail="data_id is required")
    
    task = task_manager.get_task(data_id)
    if not task or not task.get("result"):
        raise HTTPException(status_code=404, detail="Data not found")
    
    try:
        df = pd.DataFrame(task["result"])
        
        # Import cleaning service
        from app.services.data_cleaner import auto_clean
        
        # Perform auto-cleaning
        cleaned_df, cleaning_report = auto_clean(df)
        
        # Store cleaned data in task manager
        cleaned_data_id = task_manager.create_task("auto_clean", {"parent_id": data_id})
        task_manager.update_task(cleaned_data_id, status="completed", result=cleaned_df.to_dict(orient='records'))
        
        # Get column info for cleaned data
        from app.services.processor import get_column_info
        
        return {
            "cleaned_data_id": cleaned_data_id,
            "cleaning_report": cleaning_report,
            "preview": cleaned_df.head(100).to_dict(orient='records'),
            "columns": get_column_info(cleaned_df),
            "total_rows": len(cleaned_df)
        }
    except Exception as e:
        import traceback
        print(f"Error in auto_clean: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Auto-clean failed: {str(e)}")

@router.post("/explain-dataset")
async def explain_dataset(request: dict):
    """
    Analyze and explain what the dataset contains.
    
    Request body:
    - data_id: ID of the dataset to explain
    
    Returns:
    - overview: Dataset metadata (rows, columns, completeness)
    - column_insights: Detailed statistics per column
    - explanation: Plain English description of the dataset
    - inferred_purpose: Best guess at what the dataset is about
    """
    from app.models.schemas import DataIdRequest
    
    # Validate request
    if isinstance(request, dict):
        data_id = request.get("data_id")
    else:
        data_id = request.data_id
        
    if not data_id:
        raise HTTPException(status_code=400, detail="data_id is required")
    
    task = task_manager.get_task(data_id)
    if not task or not task.get("result"):
        raise HTTPException(status_code=404, detail="Data not found")
    
    try:
        df = pd.DataFrame(task["result"])
        
        # Import explanation service
        from app.services.dataset_explainer import analyze_dataset, generate_explanation
        
        # Perform analysis
        analysis = analyze_dataset(df)
        explanation_data = generate_explanation(df, analysis)
        
        return {
            "overview": analysis["overview"],
            "column_insights": {
                "columns": analysis["columns"],
                "numeric": analysis["numeric_insights"],
                "categorical": analysis["categorical_insights"]
            },
            "explanation": explanation_data["explanation"],
            "inferred_purpose": explanation_data["inferred_purpose"],
            "column_descriptions": explanation_data["column_descriptions"],
            "suggested_use_cases": explanation_data["suggested_use_cases"]
        }
    except Exception as e:
        import traceback
        print(f"Error in explain_dataset: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Dataset explanation failed: {str(e)}")

@router.post("/scrape-products")
async def scrape_products_endpoint(
    background_tasks: BackgroundTasks,
    request: dict
):
    """
    Scrape product-level data from e-commerce URLs using headless browser.
    
    Request body:
    - urls: List of product listing URLs to scrape
    - max_pages: Maximum pages to scrape per URL (default: 3)
    - auto_detect: Use auto-detection if site not in configs (default: False)
    
    Returns:
    - task_id: ID to track scraping progress
    """
    from app.models.schemas import ProductScrapeRequest
    
    # Validate request
    urls = request.get("urls", [])
    max_pages = request.get("max_pages", 3)
    auto_detect = request.get("auto_detect", False)
    
    if not urls:
        raise HTTPException(status_code=400, detail="urls are required")
    
    # Create task
    task_id = task_manager.create_task("product_scrape", {
        "urls": urls,
        "max_pages": max_pages,
        "auto_detect": auto_detect
    })
    
    # Start scraping in background
    async def run_product_scrape():
        try:
            from app.services.product_scraper import ProductScraper
            
            task_manager.update_task(task_id, status="running", progress=0)
            all_products = []
            total_urls = len(urls)
            
            for idx, url in enumerate(urls):
                try:
                    scraper = ProductScraper()
                    
                    if auto_detect:
                        products = await scraper.scrape_with_auto_detect(url, max_pages)
                    else:
                        products = await scraper.scrape_products(url, max_pages)
                    
                    all_products.extend(products)
                    
                    progress = int(((idx + 1) / total_urls) * 100)
                    task_manager.update_task(task_id, progress=progress)
                    
                except Exception as e:
                    print(f"Error scraping {url}: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            # Convert to result format
            result = []
            for product in all_products:
                result.append({
                    "title": product.get("title", ""),
                    "price": product.get("price"),
                    "discount": product.get("discount", ""),
                    "url": product.get("url", ""),
                    "image": product.get("image", "")
                })
            
            task_manager.update_task(
                task_id,
                status="completed",
                progress=100,
                result=result
            )
            
        except Exception as e:
            import traceback
            error_msg = f"Product scraping failed: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            task_manager.update_task(
                task_id,
                status="failed",
                error=error_msg
            )
    
    # Add to background tasks
    background_tasks.add_task(run_product_scrape)
    
    return {"task_id": task_id, "message": "Product scraping started"}



@router.post("/universal-scrape")
async def universal_scrape_endpoint(
    background_tasks: BackgroundTasks,
    request: dict
):
    """
    Universal scraper that automatically detects and extracts structured data 
    (tables, lists, articles) from any website.
    
    Request body:
    - urls: List of URLs to scrape
    - max_pages: Maximum pages to scrape per URL (default: 1)
    
    Returns:
    - task_id: ID to track scraping progress
    """
    urls = request.get("urls", [])
    max_pages = request.get("max_pages", 1)
    
    if not urls:
        raise HTTPException(status_code=400, detail="urls are required")
    
    # Create task
    task_id = task_manager.create_task("universal_scrape", {
        "urls": urls,
        "max_pages": max_pages
    })
    
    # Start scraping in background
    async def run_universal_scrape():
        try:
            from app.services.universal_scraper import UniversalScraper
            
            task_manager.update_task(task_id, status="running", progress=0)
            all_results = []
            total_urls = len(urls)
            
            scraper = UniversalScraper()
            
            for idx, url in enumerate(urls):
                try:
                    # Scrape using the new universal scraper
                    result = await scraper.scrape(url, max_pages)
                    
                    # Add metadata to each row
                    for row in result.get("data", []):
                        row["_source_url"] = url
                        row["_strategy"] = result.get("strategy")
                        all_results.append(row)
                    
                    progress = int(((idx + 1) / total_urls) * 100)
                    task_manager.update_task(task_id, progress=progress)
                    
                except Exception as e:
                    print(f"Error scraping {url}: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            task_manager.update_task(
                task_id,
                status="completed",
                progress=100,
                result=all_results
            )
            
        except Exception as e:
            import traceback
            error_msg = f"Universal scraping failed: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            task_manager.update_task(
                task_id,
                status="failed",
                error=error_msg
            )
            
    background_tasks.add_task(run_universal_scrape)
    
    return {"task_id": task_id, "message": "Universal scraping started"}
