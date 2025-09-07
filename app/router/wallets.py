from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List
from datetime import datetime, timezone
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
import uuid

from ..models import Wallet, WalletCreate, WalletUpdate
from ..database import get_client
from ..config import settings
from ..utils import (
    validate_wallet_id, 
    validate_ethereum_address, 
    build_wallet_query_conditions,
    build_sort_clause
)

router = APIRouter(prefix="/wallets", tags=["wallets"])

@router.get("/", response_model=List[Wallet])
async def get_wallets(
    active_only: bool = Query(False, description="Filter for active wallets only"),
    min_score: int = Query(0, ge=0, le=10, description="Minimum score filter"),
    max_score: int = Query(10, ge=0, le=10, description="Maximum score filter"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    sort_by: str = Query("created_at", description="Sort field (created_at, score, address)"),
    sort_order: int = Query(-1, description="Sort order: 1 for ascending, -1 for descending"),
    client: bigquery.Client = Depends(get_client)
):
    """Get all wallets with optional filtering, sorting, and pagination"""
    
    # Build query conditions
    where_clause, params = build_wallet_query_conditions(active_only, min_score, max_score)
    sort_clause = build_sort_clause(sort_by, sort_order)
    
    # Build final query
    query = f"""
        SELECT id, address, score, is_active, created_at, last_updated
        FROM `{settings.FULL_TABLE_ID}`
        WHERE {where_clause}
        {sort_clause}
        LIMIT @limit OFFSET @offset
    """
    
    # Add pagination parameters
    params["limit"] = limit
    params["offset"] = offset
    
    # Fix: Properly build query parameters
    query_params = []
    for name, value in params.items():
        if isinstance(value, int):
            query_params.append(bigquery.ScalarQueryParameter(name, "INT64", value))
        elif isinstance(value, bool):
            query_params.append(bigquery.ScalarQueryParameter(name, "BOOL", value))
        else:
            query_params.append(bigquery.ScalarQueryParameter(name, "STRING", str(value)))
    
    job_config = bigquery.QueryJobConfig(query_parameters=query_params)
    
    try:
        results = client.query(query, job_config=job_config)
        wallets = [Wallet.from_bigquery_row(row) for row in results]
        return wallets
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@router.get("/count")
async def get_wallet_count(
    client: bigquery.Client = Depends(get_client)
):
    """Get the total number of wallets in the table"""
    
    query = f"""
        SELECT COUNT(*) as count
        FROM `{settings.FULL_TABLE_ID}`
    """
    
    try:
        results = client.query(query)
        count = list(results)[0].count
        return count
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
    
@router.get("/{wallet_id}", response_model=Wallet)
async def get_wallet(
    wallet_id: str, 
    client: bigquery.Client = Depends(get_client)
):
    """Get a specific wallet by ID"""
    validated_id = validate_wallet_id(wallet_id)
    
    query = f"""
        SELECT id, address, score, is_active, created_at, last_updated
        FROM `{settings.FULL_TABLE_ID}`
        WHERE id = @wallet_id
        LIMIT 1
    """
    
    job_config = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("wallet_id", "STRING", validated_id)
    ])
    
    try:
        results = client.query(query, job_config=job_config)
        rows = list(results)
        
        if not rows:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        return Wallet.from_bigquery_row(rows[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@router.get("/search/by-address", response_model=Wallet)  # Fix: Added response model
async def search_wallet_by_address(
    address: str = Query(..., min_length=42, max_length=42),
    client: bigquery.Client = Depends(get_client)
):
    """Search for a wallet by address"""
    validated_address = validate_ethereum_address(address)
    
    query = f"""
        SELECT id, address, score, is_active, created_at, last_updated
        FROM `{settings.FULL_TABLE_ID}`
        WHERE address = @address
        LIMIT 1
    """
    
    job_config = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("address", "STRING", validated_address)
    ])
    
    try:
        results = client.query(query, job_config=job_config)
        rows = list(results)
        
        if not rows:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        return Wallet.from_bigquery_row(rows[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")

@router.post("/", response_model=Wallet, status_code=201)
async def create_wallet(
    wallet_data: WalletCreate, 
    client: bigquery.Client = Depends(get_client)
):
    """Create a new wallet entry"""
    
    # Validate address format
    validated_address = validate_ethereum_address(wallet_data.address)
    
    # Check if wallet address already exists
    check_query = f"""
        SELECT COUNT(*) as count
        FROM `{settings.FULL_TABLE_ID}`
        WHERE address = @address
    """
    
    job_config = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("address", "STRING", validated_address)
    ])
    
    try:
        results = client.query(check_query, job_config=job_config)
        count = list(results)[0].count
        
        if count > 0:
            raise HTTPException(status_code=400, detail="Wallet address already exists")
        
        # Create new wallet
        wallet_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        insert_query = f"""
            INSERT INTO `{settings.FULL_TABLE_ID}` 
            (id, address, score, is_active, created_at, last_updated)
            VALUES (@id, @address, @score, @is_active, @created_at, @last_updated)
        """
        
        job_config = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("id", "STRING", wallet_id),
            bigquery.ScalarQueryParameter("address", "STRING", validated_address),
            bigquery.ScalarQueryParameter("score", "INT64", wallet_data.score),
            bigquery.ScalarQueryParameter("is_active", "BOOL", wallet_data.is_active),
            bigquery.ScalarQueryParameter("created_at", "TIMESTAMP", now),
            bigquery.ScalarQueryParameter("last_updated", "TIMESTAMP", now),
        ])
        
        client.query(insert_query, job_config=job_config).result()
        
        # Return the created wallet
        return Wallet(
            id=wallet_id,
            address=validated_address,
            score=wallet_data.score,
            is_active=wallet_data.is_active,
            created_at=now,
            last_updated=now
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Insert failed: {str(e)}")

@router.put("/{wallet_id}", response_model=Wallet)
async def update_wallet(
    wallet_id: str, 
    wallet_update: WalletUpdate, 
    client: bigquery.Client = Depends(get_client)
):
    """Update an existing wallet"""
    validated_id = validate_wallet_id(wallet_id)
    
    # Check if wallet exists
    check_query = f"""
        SELECT id, address, score, is_active, created_at, last_updated
        FROM `{settings.FULL_TABLE_ID}`
        WHERE id = @wallet_id
        LIMIT 1
    """
    
    job_config = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("wallet_id", "STRING", validated_id)
    ])
    
    try:
        results = client.query(check_query, job_config=job_config)
        rows = list(results)
        
        if not rows:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        existing_wallet = rows[0]
        
        # Build update query dynamically
        update_fields = []
        params = [bigquery.ScalarQueryParameter("wallet_id", "STRING", validated_id)]
        
        if wallet_update.score is not None:
            update_fields.append("score = @new_score")
            params.append(bigquery.ScalarQueryParameter("new_score", "INT64", wallet_update.score))
        
        if wallet_update.is_active is not None:
            update_fields.append("is_active = @new_is_active")
            params.append(bigquery.ScalarQueryParameter("new_is_active", "BOOL", wallet_update.is_active))
        
        if not update_fields:
            # No fields to update, return existing wallet
            return Wallet.from_bigquery_row(existing_wallet)
        
        now = datetime.now(timezone.utc)
        update_fields.append("last_updated = @last_updated")
        params.append(bigquery.ScalarQueryParameter("last_updated", "TIMESTAMP", now))
        
        update_query = f"""
            UPDATE `{settings.FULL_TABLE_ID}`
            SET {', '.join(update_fields)}
            WHERE id = @wallet_id
        """
        
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        client.query(update_query, job_config=job_config).result()
        
        # Return updated wallet
        updated_wallet = Wallet.from_bigquery_row(existing_wallet)
        if wallet_update.score is not None:
            updated_wallet.score = wallet_update.score
        if wallet_update.is_active is not None:
            updated_wallet.is_active = wallet_update.is_active
        updated_wallet.last_updated = now
        
        return updated_wallet
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")

@router.delete("/{wallet_id}")
async def delete_wallet(
    wallet_id: str, 
    client: bigquery.Client = Depends(get_client)
):
    """Delete a wallet"""
    validated_id = validate_wallet_id(wallet_id)
    
    # First get the wallet to return in response
    get_query = f"""
        SELECT id, address, score, is_active, created_at, last_updated
        FROM `{settings.FULL_TABLE_ID}`
        WHERE id = @wallet_id
        LIMIT 1
    """
    
    job_config = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("wallet_id", "STRING", validated_id)
    ])
    
    try:
        results = client.query(get_query, job_config=job_config)
        rows = list(results)
        
        if not rows:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        wallet = Wallet.from_bigquery_row(rows[0])
        
        # Delete the wallet
        delete_query = f"""
            DELETE FROM `{settings.FULL_TABLE_ID}`
            WHERE id = @wallet_id
        """
        
        client.query(delete_query, job_config=job_config).result()
        
        return {
            "message": "Wallet deleted successfully",
            "deleted_wallet": wallet
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")

@router.post("/bulk", status_code=201)
async def bulk_create_wallets(
    wallets: List[WalletCreate], 
    client: bigquery.Client = Depends(get_client)
):
    """Bulk create multiple wallets"""
    if len(wallets) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 wallets per bulk operation")
    
    # Validate all addresses first
    validated_addresses = []
    for wallet_data in wallets:
        validated_address = validate_ethereum_address(wallet_data.address)
        validated_addresses.append(validated_address)
    
    # Check for existing addresses
    if validated_addresses:
        placeholders = ','.join([f'@addr_{i}' for i in range(len(validated_addresses))])
        check_query = f"""
            SELECT address
            FROM `{settings.FULL_TABLE_ID}`
            WHERE address IN ({placeholders})
        """
        
        params = [
            bigquery.ScalarQueryParameter(f"addr_{i}", "STRING", addr)
            for i, addr in enumerate(validated_addresses)
        ]
        
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        
        try:
            results = client.query(check_query, job_config=job_config)
            existing_addresses = {row.address for row in results}
            
            # Check if any addresses already exist
            for addr in validated_addresses:
                if addr in existing_addresses:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Wallet address already exists: {addr}"
                    )
            
            # Prepare bulk insert
            now = datetime.now(timezone.utc)
            rows_to_insert = []
            
            for i, wallet_data in enumerate(wallets):
                rows_to_insert.append({
                    "id": str(uuid.uuid4()),
                    "address": validated_addresses[i],
                    "score": wallet_data.score,
                    "is_active": wallet_data.is_active,
                    "created_at": now,
                    "last_updated": now
                })
            
            # Insert rows
            table = client.get_table(settings.FULL_TABLE_ID)
            errors = client.insert_rows_json(table, rows_to_insert)
            
            if errors:
                raise HTTPException(status_code=500, detail=f"Insert errors: {errors}")
            
            return {
                "message": f"Successfully created {len(rows_to_insert)} wallets",
                "inserted_ids": [row["id"] for row in rows_to_insert]
            }
        
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Bulk insert failed: {str(e)}")
    
    return {"message": "No wallets to insert", "inserted_ids": []}