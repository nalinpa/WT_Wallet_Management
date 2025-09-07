from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .config import settings
from .database import connect_to_bigquery, close_bigquery_connection
from .router import wallets_router
from .router import frontend_router
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_bigquery()
    yield
    # Shutdown
    await close_bigquery_connection()

app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(wallets_router)
app.include_router(frontend_router)

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": f"{settings.API_TITLE} with BigQuery",
        "version": settings.API_VERSION,
        "project": settings.GOOGLE_CLOUD_PROJECT,
        "dataset": settings.BIGQUERY_DATASET,
        "table": settings.BIGQUERY_TABLE,
        "full_table_id": settings.FULL_TABLE_ID,
        "endpoints": {
            "GET /wallets": "Get all wallets",
            "GET /wallets/{wallet_id}": "Get wallet by ID",
            "POST /wallets": "Create new wallet",
            "PUT /wallets/{wallet_id}": "Update wallet",
            "DELETE /wallets/{wallet_id}": "Delete wallet",
            "GET /wallets/search/by-address": "Search wallets by address",
            "POST /wallets/bulk": "Bulk create wallets"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "database": "BigQuery"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )