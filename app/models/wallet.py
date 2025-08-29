from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")

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
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime
    last_updated: datetime

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str,
            datetime: lambda v: v.isoformat()
        }