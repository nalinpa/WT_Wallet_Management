from fastapi import HTTPException
import uuid
import re

def validate_wallet_id(id_string: str) -> str:
    """Validate wallet ID format (UUID)"""
    try:
        uuid.UUID(id_string)
        return id_string
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid wallet ID format")

def validate_ethereum_address(address: str) -> str:
    """Validate Ethereum address format"""
    if not address.startswith('0x') or len(address) != 42:
        raise HTTPException(status_code=400, detail="Invalid Ethereum address format")
    
    # Check if it contains only valid hex characters
    if not re.match(r'^0x[a-fA-F0-9]{40}$', address):
        raise HTTPException(status_code=400, detail="Invalid Ethereum address format")
    
    return address.lower()

def build_wallet_query_conditions(
    active_only: bool = False,
    min_score: int = 0,
    max_score: int = 10
) -> tuple[str, dict]:
    """Build SQL WHERE conditions and parameters for wallet queries"""
    conditions = []
    params = {}
    
    # Score range filter
    conditions.append("score >= @min_score AND score <= @max_score")
    params["min_score"] = min_score
    params["max_score"] = max_score
    
    # Active filter
    if active_only:
        conditions.append("is_active = @is_active")
        params["is_active"] = True
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    return where_clause, params

def escape_sql_string(value: str) -> str:
    """Escape string for SQL to prevent injection"""
    return value.replace("'", "''")

def build_sort_clause(sort_by: str, sort_order: int) -> str:
    """Build SQL ORDER BY clause"""
    # Validate sort_by to prevent injection
    valid_sort_fields = ["created_at", "score", "address", "last_updated", "is_active"]
    if sort_by not in valid_sort_fields:
        sort_by = "created_at"
    
    order = "ASC" if sort_order == 1 else "DESC"
    return f"ORDER BY {sort_by} {order}"