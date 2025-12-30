# Deployment Guide

This project is structured as a monorepo with a FastAPI backend and a Vite frontend.

## 1. Deploy Backend (Render)

We use Docker to ensure Playwright and its dependencies are correctly installed.

1.  Create a new **Web Service** on [Render](https://render.com/).
2.  Connect your GitHub repository.
3.  Render will automatically detect the `render.yaml` or you can configure it manually:
    *   **Environment**: `Docker`
    *   **Docker Context**: `.` (Root of the repo)
    *   **Dockerfile Path**: `Dockerfile`
4.  **Important**: Playwright requires a decent amount of RAM. Use at least the **Starter** plan (not the Free tier) for reliable scraping.
5.  Once deployed, copy your backend URL (e.g., `https://your-backend.onrender.com`).

## 2. Deploy Frontend (Vercel)

1.  Create a new project on [Vercel](https://vercel.com/).
2.  Connect your GitHub repository.
3.  Configure the project:
    *   **Framework Preset**: `Vite`
    *   **Root Directory**: `frontend`
    *   **Build Command**: `npm run build`
    *   **Output Directory**: `dist`
4.  **Environment Variables**:
    *   Add `VITE_API_BASE`: `https://your-backend.onrender.com/api` (Replace with your actual Render URL).
5.  Deploy!

## 3. Post-Deployment Check

1.  Open your Vercel URL.
2.  Try to scrape a simple URL (e.g., `https://example.com`) to verify the connection between frontend and backend.
3.  Check Render logs if you see any "Timeout" or "NotImplementedError" (though the Docker setup should prevent these).
