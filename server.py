"""
Backward-compatibility entry point for backend.main.
Allows running via `python server.py` or `uvicorn server:app`.
"""
from backend.main import app, create_app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
