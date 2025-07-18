# main.py
from src.app import app

# This file is used to run the application
# The app is imported from src.app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        access_log=True,
        log_level="info"
    )
