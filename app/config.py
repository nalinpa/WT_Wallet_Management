import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
     # BigQuery Configuration
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    BIGQUERY_DATASET: str = os.getenv("BIGQUERY_DATASET", "crypto_tracker")
    BIGQUERY_TABLE: str = os.getenv("BIGQUERY_TABLE", "smart_wallets")
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    
    # Full table reference
    @property
    def FULL_TABLE_ID(self) -> str:
        return f"{self.GOOGLE_CLOUD_PROJECT}.{self.BIGQUERY_DATASET}.{self.BIGQUERY_TABLE}"
    

    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "Password!!")
    
    # CORS Configuration
    ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "*").split(",")
    
    # API Metadata
    API_TITLE: str = "Wallet Management API"
    API_DESCRIPTION: str = "API for managing wallet entries with scores using MongoDB"
    API_VERSION: str = "1.0.0"

settings = Settings()