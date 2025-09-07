from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
import uuid

class WalletBase(BaseModel):
    address: str = Field(..., min_length=42, max_length=42, description="Ethereum wallet address")
    score: int = Field(..., ge=0, le=10, description="Wallet score between 0 and 10")
    is_active: bool = Field(default=True, description="Whether the wallet is active")

class WalletCreate(WalletBase):
    pass

class WalletUpdate(BaseModel):
    score: Optional[int] = Field(None, ge=0, le=10, description="Updated wallet score")
    is_active: Optional[bool] = Field(None, description="Updated active status")

class Wallet(WalletBase):
    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={datetime: lambda v: v.isoformat()}
    )
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime
    last_updated: datetime

    @classmethod
    def from_bigquery_row(cls, row):
        """Create Wallet instance from BigQuery row"""
        return cls(
            id=row.id,
            address=row.address,
            score=row.score,
            is_active=row.is_active,
            created_at=row.created_at,
            last_updated=row.last_updated
        )