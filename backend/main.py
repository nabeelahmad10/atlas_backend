"""
Atlas Marketing OS API — Main FastAPI Application
AI-Native Mini CRM for Marketing & Engagement

Endpoints:
- /api/customers — Customer management
- /api/segments — Audience segmentation
- /api/campaigns — Campaign triggering
- /api/receipts — Delivery receipt webhooks
- /api/analytics — Performance insights
- /api/ai — AI-powered segmentation & messaging
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import time
import json
import logging
from database import init_db
from seed_data import seed
from dotenv import load_dotenv

load_dotenv()

from routes.customers import router as customers_router
from routes.segments import router as segments_router
from routes.campaigns import router as campaigns_router
from routes.receipts import router as receipts_router
from routes.analytics import router as analytics_router
from routes.ai import router as ai_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and seed data on startup."""
    print("[START] Starting Atlas Marketing OS API...")
    await init_db()
    await seed()
    print("[READY] CRM API ready!")
    yield
    print("[STOP] Shutting down CRM API...")


app = FastAPI(
    title="Atlas Marketing OS API",
    description="AI-Native Mini CRM for Marketing & Engagement — Built for Xeno",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://*.vercel.app",
        "*",  # For development; restrict in production
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("atlas_marketing_os")

@app.middleware("http")
async def structured_logging_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    # Exclude health check from spamming logs
    if request.url.path != "/health":
        log_dict = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "service": "api_backend",
            "level": "INFO",
            "message": f"{request.method} {request.url.path}",
            "metadata": {
                "status_code": response.status_code,
                "process_time_ms": round(process_time * 1000, 2),
                "client_ip": request.client.host if request.client else "unknown"
            }
        }
        logger.info(json.dumps(log_dict))
        
    return response

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint for PaaS deployments (Railway/Render)."""
    return {"status": "healthy"}

# Register route modules
app.include_router(customers_router)
app.include_router(segments_router)
app.include_router(campaigns_router)
app.include_router(receipts_router)
app.include_router(analytics_router)
app.include_router(ai_router)


@app.get("/")
async def root():
    """Health check & API info."""
    return {
        "name": "Atlas Marketing OS API",
        "version": "1.0.0",
        "status": "healthy",
        "docs": "/docs",
        "description": "AI-Native Mini CRM for Marketing & Engagement",
        "endpoints": {
            "customers": "/api/customers",
            "segments": "/api/segments",
            "campaigns": "/api/campaigns",
            "receipts": "/api/receipts",
            "analytics": "/api/analytics",
            "ai_segment": "/api/ai/segment",
            "ai_message": "/api/ai/message",
        },
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
