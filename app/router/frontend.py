import base64
import os
from pathlib import Path
from fastapi import APIRouter, Form, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
import json
from google.cloud import bigquery

from ..config import settings
from ..database import get_client

router = APIRouter(tags=["frontend"])

# Get the absolute path to the templates directory
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

@router.get("/wallets", response_class=HTMLResponse)
async def get_wallets_html(
    request: Request,
    active_only: bool = False,
    min_score: int = 0,
    max_score: int = 10,
    limit: int = 10,
    offset: int = 0,
    sort_by: str = "created_at",
    sort_order: int = -1,
    client: bigquery.Client = Depends(get_client)
):
    """Get wallets as HTML table"""
    
    try:
        # Build WHERE clause
        where_conditions = [
            f"score >= {min_score}",
            f"score <= {max_score}"
        ]
        
        if active_only:
            where_conditions.append("is_active = TRUE")
        
        where_clause = " AND ".join(where_conditions)
        
        # Build ORDER BY clause
        order_direction = "DESC" if sort_order == -1 else "ASC"
        
        # Get wallets with pagination
        wallets_query = f"""
            SELECT id, address, score, is_active, created_at, last_updated
            FROM `{settings.FULL_TABLE_ID}`
            WHERE {where_clause}
            ORDER BY {sort_by} {order_direction}
            LIMIT {limit} OFFSET {offset}
        """
        
        wallets_result = client.query(wallets_query)
        wallets = [
            {
                "id": row.id,
                "address": row.address,
                "score": row.score,
                "is_active": row.is_active,
                "created_at": row.created_at,
                "last_updated": row.last_updated
            }
            for row in wallets_result
        ]
        
        # Get total count for pagination
        count_query = f"""
            SELECT COUNT(*) as total_count
            FROM `{settings.FULL_TABLE_ID}`
            WHERE {where_clause}
        """
        count_result = client.query(count_query)
        total_count = list(count_result)[0].total_count
        
    except Exception as e:
        wallets = []
        total_count = 0
    
    return templates.TemplateResponse("partials/wallet_list.html", {
        "request": request,
        "wallets": wallets,
        "total_count": total_count,
        "current_page": (offset // limit) + 1,
        "total_pages": max(1, (total_count + limit - 1) // limit),
        "limit": limit,
        "has_previous": offset > 0,
        "has_next": offset + limit < total_count
    })

@router.get("/wallets/search/by-address", response_class=HTMLResponse)
async def search_wallet_html(
    request: Request,
    address: str,
    client: bigquery.Client = Depends(get_client)
):
    """Search wallet by address and return HTML"""
    
    try:
        search_query = f"""
            SELECT id, address, score, is_active, created_at, last_updated
            FROM `{settings.FULL_TABLE_ID}`
            WHERE address = @address
            LIMIT 1
        """
        
        job_config = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("address", "STRING", address.lower())
        ])
        
        result = client.query(search_query, job_config=job_config)
        rows = list(result)
        
        if not rows:
            return templates.TemplateResponse("partials/wallet_not_found.html", {
                "request": request,
                "address": address
            })
        
        row = rows[0]
        wallet = {
            "id": row.id,
            "address": row.address,
            "score": row.score,
            "is_active": row.is_active,
            "created_at": row.created_at,
            "last_updated": row.last_updated
        }
        
        return templates.TemplateResponse("partials/wallet_card.html", {
            "request": request,
            "wallet": wallet
        })
        
    except Exception as e:
        return templates.TemplateResponse("partials/wallet_not_found.html", {
            "request": request,
            "address": address
        })

# Page routes (full pages, not just partials)
@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@router.get("/wallets-view", response_class=HTMLResponse)
async def wallets_page(request: Request):
    """View all wallets page"""
    return templates.TemplateResponse("wallets.html", {"request": request})

@router.get("/wallets-add", response_class=HTMLResponse)
async def add_wallet_page(request: Request):
    """Add wallet form page"""
    return templates.TemplateResponse("add_wallet.html", {"request": request})

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/authenticate")
async def authenticate(request: Request, password: str = Form(...)):
    """Handle login form submission"""
    ADMIN_PASSWORD = getattr(settings, 'ADMIN_PASSWORD', 'admin123')  # Default password if not set
    import secrets
    
    if secrets.compare_digest(password, ADMIN_PASSWORD):
        # Set a session cookie and redirect
        response = RedirectResponse(url="/dashboard", status_code=302)
        # Create basic auth header for the session
        credentials = base64.b64encode(f":{password}".encode()).decode()
        response.set_cookie(key="auth", value=credentials, httponly=True, max_age=3600)
        return response
    else:
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "error": True
        })