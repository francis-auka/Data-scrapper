# Enhanced Product Scraper - Setup Guide

## Installation Steps

### 1. Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Install Playwright Browsers

After installing playwright, you need to install the browser binaries:

```bash
playwright install chromium
```

This will download Chromium (~300MB). You only need to do this once.

### 3. Restart Backend Server

```bash
python -m app.main
```

## Usage

### Frontend

1. Go to the **Scraper** tab
2. Check the "🛍️ Product-Level Scraping" checkbox
3. Set max pages (1-10)
4. Enter product listing URLs (one per line)
5. Click "Start Product Scraping"

### Supported Sites

The scraper has built-in configurations for:
- **Amazon** - Product search/listing pages
- **eBay** - Search results
- **Shopify** stores - Any Shopify-powered store
- **WooCommerce** - WordPress/WooCommerce sites
- **Generic** - Any e-commerce site (auto-detection)

### Example URLs to Test

```
# Amazon (may require cookies/captcha handling)
https://www.amazon.com/s?k=laptop

# Generic Shopify store
https://demo.vercel.store/search

# Or any product listing page
```

## How It Works

1. **Headless Browser**: Uses Playwright to render JavaScript
2. **Smart Detection**: Auto-detects product containers and fields
3. **Pagination**: Follows "Next" links automatically
4. **Data Extraction**: Extracts title, price, discount, URL, image
5. **CSV Export**: Download results as CSV with one row per product

## Extracted Fields

- **Title** - Product name
- **Price** - Numeric price value
- **Discount** - Discount badge/text (if any)
- **URL** - Direct product link
- **Image** - Product image URL

## Configuration

### Adding New Sites

Edit `backend/app/config/site_configs.json`:

```json
{
  "mysite": {
    "name": "My Site",
    "selectors": {
      "product_container": [".product-card"],
      "title": ["h2.title"],
      "price": [".price"],
      "image": ["img.product-img"],
      "link": ["a.product-link"],
      "next_page": [".pagination-next"]
    },
    "wait_for": ".product-card",
    "max_pages": 5
  }
}
```

## Troubleshooting

### "No products found"
- Site may use different selectors
- Try enabling auto-detect mode in code
- Check if site requires login/cookies

### Slow scraping
- This is normal - headless browser is slower than HTTP requests
- Each page waits 2s for JS rendering
- Rate limiting adds 2s between pages

### Playwright installation fails
- Ensure you have ~500MB free disk space
- Run: `playwright install --help` for options
- Windows users: May need Visual C++ redistributables

## API Endpoint

```python
POST /api/scrape-products
{
  "urls": ["https://example.com/products"],
  "max_pages": 3,
  "auto_detect": false
}
```

Response:
```python
{
  "task_id": "abc123",
  "message": "Product scraping started"
}
```

Then poll `/api/tasks/{task_id}` for status and results.
