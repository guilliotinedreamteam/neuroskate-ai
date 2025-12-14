import uvicorn
import os

def main():
    """
    Entry point for the application.
    Runs the FastAPI app via Uvicorn.
    """
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("ecom_dominator.api:app", host="0.0.0.0", port=port, reload=False)

if __name__ == "__main__":
    main()
