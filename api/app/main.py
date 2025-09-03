
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import logging
import secrets
from .config import settings
from .routes import api, dashboard, reports
from .telegram_webhook import router as telegram_router
from .db import create_tables

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Security configuration
security = HTTPBasic()

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="A production-ready Python trading bot for Binance spot trading",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting and security middleware
from fastapi import Request
import time
from collections import defaultdict

# Simple rate limiting
request_counts = defaultdict(list)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Simple rate limiting middleware"""
    client_ip = request.client.host
    
    # Clean old requests (older than 1 minute)
    current_time = time.time()
    request_counts[client_ip] = [req_time for req_time in request_counts[client_ip] 
                                if current_time - req_time < 60]
    
    # Check rate limit (60 requests per minute)
    if len(request_counts[client_ip]) >= 60:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Add current request
    request_counts[client_ip].append(current_time)
    
    response = await call_next(request)
    return response

# Mount static files
app.mount("/static", StaticFiles(directory="api/app/static"), name="static")

# Include routers
app.include_router(api.router, prefix="/api", tags=["api"])
app.include_router(dashboard.router, tags=["dashboard"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(telegram_router, prefix="/telegram", tags=["telegram"])


@app.get("/healthz")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "mode": settings.MODE,
        "tz": settings.TZ
    }

@app.get("/")
async def root():
    """Root endpoint - redirect to dashboard"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/dashboard")

@app.get("/public-info")
async def public_info():
    """Public information endpoint (no authentication required)"""
    return {
        "service": "SolSpot Trading Bot",
        "version": "1.0.0",
        "status": "running",
        "timestamp": time.time()
    }


@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    logging.info(f"{settings.APP_NAME} starting up...")
    # Create database tables
    create_tables()
    logging.info("Database tables created/verified")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    logging.info(f"{settings.APP_NAME} shutting down...")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
