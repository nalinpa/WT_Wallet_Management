from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Annotated
from datetime import datetime
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        from pydantic_core import core_schema
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(ObjectId),
                core_schema.chain_schema([
                    core_schema.str_schema(),
                    core_schema.no_info_plain_validator_function(cls.validate),
                ])
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x)
            ),
        )

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

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
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str, datetime: lambda v: v.isoformat()}
    )
    
    id: Annotated[PyObjectId, Field(default_factory=PyObjectId, alias="_id")]
    created_at: datetime
    last_updated: datetime