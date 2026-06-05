import webbrowser
import threading
import time
import uvicorn

def open_browser():
    """
    Waits briefly for the Uvicorn server to initialize,
    then automatically opens the default web browser to the application page.
    """
    time.sleep(1.5)
    url = "http://127.0.0.1:8000"
    print(f"\n[Baymax] Auto-launching browser to: {url}\n")
    webbrowser.open(url)

if __name__ == "__main__":
    # Start the browser auto-opener thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Run the Uvicorn ASGI server
    # Reload is disabled to avoid starting double instances of webbrowser threads on reload
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False
    )
