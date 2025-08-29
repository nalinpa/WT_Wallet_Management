from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List
from datetime import datetime

from ..models import Wallet, WalletCreate, WalletUpdate
from ..database import get_collection
from ..utils import wallet_helper, validate_object_id, validate_ethereum_address, build_wallet_query

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
    coll = Depends(get_collection)
):
    """Get all wallets with optional filtering, sorting, and pagination"""
    
    # Build query filter
    query_filter = build_wallet_query(active_only, min_score, max_score)
    
    # Build sort criteria
    sort_criteria = [(sort_by, sort_order)]
    
    # Execute query with pagination
    cursor = coll.find(query_filter).sort(sort_criteria).skip(offset).limit(limit)
    wallets = await cursor.to_list(length=limit)
    
    return [wallet_helper(wallet) for wallet in wallets]

@router.get("/{wallet_id}", response_model=Wallet)
async def get_wallet(wallet_id: str, coll = Depends(get_collection)):
    """Get a specific wallet by ID"""
    object_id = validate_object_id(wallet_id)
    
    wallet = await coll.find_one({"_id": object_id})
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    return wallet_helper(wallet)

@router.get("/search/by-address")
async def search_wallet_by_address(
    address: str = Query(..., min_length=42, max_length=42),
    coll = Depends(get_collection)
):
    """Search for a wallet by address"""
    validated_address = validate_ethereum_address(address)
    
    wallet = await coll.find_one({"address": validated_address})
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    return wallet_helper(wallet)

@router.post("/", response_model=Wallet, status_code=201)
async def create_wallet(wallet_data: WalletCreate, coll = Depends(get_collection)):
    """Create a new wallet entry"""
    
    # Validate address format
    validated_address = validate_ethereum_address(wallet_data.address)
    
    # Check if wallet address already exists
    existing_wallet = await coll.find_one({"address": validated_address})
    if existing_wallet:
        raise HTTPException(status_code=400, detail="Wallet address already exists")
    
    now = datetime.utcnow()
    wallet_dict = {
        "address": validated_address,
        "score": wallet_data.score,
        "is_active": wallet_data.is_active,
        "created_at": now,
        "last_updated": now
    }
    
    result = await coll.insert_one(wallet_dict)
    
    # Fetch the created wallet
    new_wallet = await coll.find_one({"_id": result.inserted_id})
    return wallet_helper(new_wallet)

@router.put("/{wallet_id}", response_model=Wallet)
async def update_wallet(
    wallet_id: str, 
    wallet_update: WalletUpdate, 
    coll = Depends(get_collection)
):
    """Update an existing wallet"""
    object_id = validate_object_id(wallet_id)
    
    # Check if wallet exists
    existing_wallet = await coll.find_one({"_id": object_id})
    if not existing_wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    # Build update document
    update_data = {"last_updated": datetime.utcnow()}
    
    if wallet_update.score is not None:
        update_data["score"] = wallet_update.score
    
    if wallet_update.is_active is not None:
        update_data["is_active"] = wallet_update.is_active
    
    # Update the wallet
    await coll.update_one(
        {"_id": object_id},
        {"$set": update_data}
    )
    
    # Fetch and return updated wallet
    updated_wallet = await coll.find_one({"_id": object_id})
    return wallet_helper(updated_wallet)

@router.delete("/{wallet_id}")
async def delete_wallet(wallet_id: str, coll = Depends(get_collection)):
    """Delete a wallet"""
    object_id = validate_object_id(wallet_id)
    
    # Find and delete the wallet
    wallet = await coll.find_one({"_id": object_id})
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    
    await coll.delete_one({"_id": object_id})
    
    return {
        "message": "Wallet deleted successfully", 
        "deleted_wallet": wallet_helper(wallet)
    }

@router.post("/bulk", status_code=201)
async def bulk_create_wallets(
    wallets: List[WalletCreate], 
    coll = Depends(get_collection)
):
    """Bulk create multiple wallets"""
    if len(wallets) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 wallets per bulk operation")
    
    now = datetime.utcnow()
    wallet_docs = []
    addresses_to_check = []
    
    # Validate all addresses first
    for wallet_data in wallets:
        validated_address = validate_ethereum_address(wallet_data.address)
        addresses_to_check.append(validated_address)
    
    # Check for existing addresses
    existing_wallets = await coll.find({"address": {"$in": addresses_to_check}}).to_list(length=None)
    existing_addresses = {w["address"] for w in existing_wallets}
    
    for i, wallet_data in enumerate(wallets):
        validated_address = addresses_to_check[i]
        
        if validated_address in existing_addresses:
            raise HTTPException(
                status_code=400, 
                detail=f"Wallet address already exists: {wallet_data.address}"
            )
        
        wallet_docs.append({
            "address": validated_address,
            "score": wallet_data.score,
            "is_active": wallet_data.is_active,
            "created_at": now,
            "last_updated": now
        })
    
    # Insert all wallets
    result = await coll.insert_many(wallet_docs)
    
    return {
        "message": f"Successfully created {len(result.inserted_ids)} wallets",
        "inserted_ids": [str(id) for id in result.inserted_ids]
    }