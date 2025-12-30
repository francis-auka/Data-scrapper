# Data Scraper

A powerful, full-stack web scraping application designed to extract product data from e-commerce websites. Built with FastAPI (Backend) and React (Frontend), it features a modern UI, real-time progress tracking, and support for both static and dynamic (JavaScript-rendered) websites.

## 🚀 Live Demo
**Frontend:** [https://data-scrapper-tan.vercel.app/](https://data-scrapper-tan.vercel.app/)
**Backend:** [https://data-scrapper-7hwh.onrender.com](https://data-scrapper-7hwh.onrender.com)

## Features

-   **Multi-Site Support:** Pre-configured for major e-commerce platforms:
    -   Jumia
    -   Amazon
    -   eBay
    -   Shopify Stores
    -   WooCommerce Stores
-   **Dynamic Scraping:** Uses Playwright to handle JavaScript-heavy sites and pagination.
-   **Auto-Detection:** Intelligent selector detection for unknown websites.
-   **Data Cleaning:** Built-in tools to clean and normalize scraped data (price formatting, text trimming).
-   **Export:** Download scraped data as CSV.
-   **Real-time Monitoring:** Track scraping progress and view logs in real-time.
-   **Modern UI:** Responsive and intuitive interface built with React and Tailwind CSS.

## Tech Stack

### Backend
-   **FastAPI:** High-performance web framework for building APIs.
-   **Playwright:** Headless browser automation for dynamic scraping.
-   **BeautifulSoup4:** HTML parsing for static content.
-   **Pandas:** Data manipulation and cleaning.
-   **Uvicorn:** ASGI server.

### Frontend
-   **React:** Frontend library for building user interfaces.
-   **Vite:** Next-generation frontend tooling.
-   **Tailwind CSS:** Utility-first CSS framework.
-   **Lucide React:** Beautiful & consistent icons.

## Installation

### Prerequisites
-   Python 3.8+
-   Node.js 16+
-   Git

### Backend Setup

1.  Navigate to the backend directory:
    ```bash
    cd backend
    ```

2.  Create a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4.  Install Playwright browsers:
    ```bash
    playwright install chromium
    ```

5.  Run the server:
    
    **On Windows (Required for Playwright):**
    ```bash
    python run.py
    ```

    **On Mac/Linux:**
    ```bash
    uvicorn app.main:app --reload
    ```
    The backend will be available at `http://localhost:8000`.

### Frontend Setup

1.  Navigate to the frontend directory:
    ```bash
    cd frontend
    ```

2.  Install dependencies:
    ```bash
    npm install
    ```

3.  Start the development server:
    ```bash
    npm run dev
    ```
    The application will be available at `http://localhost:5173`.

## Usage

1.  Open the application in your browser.
2.  **Scraper Tab:**
    -   Enter the URL(s) you want to scrape.
    -   Toggle "Product-Level Scraping" for detailed product data (title, price, image, etc.).
    -   Click "Start Scraping".
3.  **History Tab:**
    -   View past scraping tasks.
    -   Download results as CSV.
4.  **Data Cleaning Tab:**
    -   Select a scraping task.
    -   Choose cleaning operations (e.g., Remove Duplicates, Normalize Prices).
    -   Click "Clean Data".

## Configuration

Site-specific configurations are stored in `backend/app/config/site_configs.json`. You can add or modify selectors for different websites here.

Example Configuration:
```json
"jumia": {
    "name": "Jumia",
    "selectors": {
        "product_container": ["article.prd"],
        "title": ["h3.name"],
        "price": [".prc"],
        "image": ["img.img"],
        "link": ["a.core"]
    }
}
```

## License

MIT
