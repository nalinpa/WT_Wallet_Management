import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    # MongoDB Configuration
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "wallet_db")
    COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "wallets")
    
    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # CORS Configuration
    ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    
    # API Metadata
    API_TITLE: str = "Wallet Management API"
    API_DESCRIPTION: str = "API for managing wallet entries with scores using MongoDB"
    API_VERSION: str = "1.0.0"

settings = Settings()