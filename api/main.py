# main.py
import sys
import os

# Add the current directory to the path so that imports work correctly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# This file is used to run the application
# The app is imported from api.src.app
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