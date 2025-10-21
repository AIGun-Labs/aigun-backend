"""
AI Gun Backend Service Main Entry Point
This file serves as the primary entry point for the FastAPI application, 
responsible for creating the application instance and starting the server
"""

import uvicorn
from app import create_app
from app.views import on_init

app = create_app()

on_init(app)


if __name__ == '__main__':
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)