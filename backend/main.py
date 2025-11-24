"""
Simple test server for Railway deployment.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="Orca Test Server", version="0.1.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "message": "Orca Test Server",
        "status": "running",
        "environment": os.getenv("RAILWAY_ENVIRONMENT", "local")
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/test")
async def test():
    return {
        "message": "Test endpoint works!",
        "port": os.getenv("PORT", "8000"),
        "railway": os.getenv("RAILWAY_ENVIRONMENT", "not on Railway")
    }

