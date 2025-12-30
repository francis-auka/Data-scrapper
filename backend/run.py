import uvicorn
import sys
import asyncio
import os

if __name__ == "__main__":
    # Fix for Playwright on Windows
    # This must be done before any asyncio loop is created
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        print("Enabled WindowsProactorEventLoopPolicy for Playwright compatibility.")

    # Run the server
    # reload=False is important because the reloader can spawn a new process 
    # that might not inherit the event loop policy correctly or use a different default.
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
