"""
Simple test server for Railway deployment.
"""
# Trigger rebuild
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import execute
import os
import sys

app = FastAPI(title="Orca Test Server", version="0.1.0")

# Log startup info for debugging
print(f"Starting server...", file=sys.stderr)
print(f"PORT env var: {os.getenv('PORT', 'not set')}", file=sys.stderr)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(execute.router)


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

