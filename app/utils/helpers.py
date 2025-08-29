from bson import ObjectId
from fastapi import HTTPException

def wallet_helper(wallet) -> dict:
    """Helper function to format wallet document"""
    if wallet:
        wallet["id"] = str(wallet["_id"])
        return wallet
    return wallet

def validate_object_id(id_string: str) -> ObjectId:
    """Validate and convert string to ObjectId"""
    if not ObjectId.is_valid(id_string):
        raise HTTPException(status_code=400, detail="Invalid wallet ID format")
    return ObjectId(id_string)

def validate_ethereum_address(address: str) -> str:
    """Validate Ethereum address format"""
    if not address.startswith('0x') or len(address) != 42:
        raise HTTPException(status_code=400, detail="Invalid Ethereum address format")
    return address.lower()

def build_wallet_query(
    active_only: bool = False,
    min_score: int = 0,
    max_score: int = 10
) -> dict:
    """Build MongoDB query filter for wallets"""
    query_filter = {
        "score": {"$gte": min_score, "$lte": max_score}
    }
    
    if active_only:
        query_filter["is_active"] = True
    
    return query_filter