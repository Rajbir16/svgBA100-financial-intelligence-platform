"""Main FastAPI Application — Sprint 6 (Days 38–40).

Mounts all modular routers under /api/v1, provides CORS for local development,
adds request timing/logging middleware, and exposes interactive OpenAPI documentation.
"""

import logging
import time
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routers import (
    companies,
    documents,
    health,
    peers,
    portfolio,
    screener,
    sectors,
    valuation,
)

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("svgBA100.api")

app = FastAPI(
    title="svgBA100 Financial Intelligence Platform API",
    version="1.0.0",
    description=(
        "Production-grade RESTful API for financial intelligence, screening, peer analysis, "
        "valuation, capital allocation, and tear-sheet downloads across the Nifty 100 universe."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# 1. CORS Middleware for local development and dashboard integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 2. Request timing and logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000.0

    # Record method, path, status, and duration
    logger.info(
        f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms:.2f}ms)"
    )
    response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
    return response


# 3. Mount Routers under /api/v1
API_V1_PREFIX = "/api/v1"

app.include_router(health.router, prefix=API_V1_PREFIX)
app.include_router(companies.router, prefix=API_V1_PREFIX)
app.include_router(screener.router, prefix=API_V1_PREFIX)
app.include_router(sectors.router, prefix=API_V1_PREFIX)
app.include_router(peers.router, prefix=API_V1_PREFIX)
app.include_router(valuation.router, prefix=API_V1_PREFIX)
app.include_router(portfolio.router, prefix=API_V1_PREFIX)
app.include_router(documents.router, prefix=API_V1_PREFIX)


@app.get("/", summary="Root health and documentation link")
def root_endpoint() -> Dict[str, Any]:
    """Root entrypoint linking to interactive documentation."""
    return {
        "platform": "svgBA100 Financial Intelligence Platform",
        "status": "online",
        "api_version": "v1",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_spec": "/openapi.json",
        "v1_base": "/api/v1",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="127.0.0.1", port=8000, reload=False)

