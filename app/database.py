from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from .config import settings
import logging

logger = logging.getLogger(__name__)

class Database:
    client: bigquery.Client = None

# Global database instance
database = Database()

async def connect_to_bigquery():
    """Create BigQuery client and ensure table exists"""
    try:
        database.client = bigquery.Client(project=settings.GOOGLE_CLOUD_PROJECT)
        
        # Test connection
        query = f"SELECT 1 as test LIMIT 1"
        list(database.client.query(query))
        
        # Ensure dataset exists
        await ensure_dataset_exists()
        
        # Ensure table exists with proper schema
        await ensure_table_exists()
        
        logger.info(f"Connected to BigQuery: {settings.FULL_TABLE_ID}")
        
    except Exception as e:
        logger.error(f"Failed to connect to BigQuery: {e}")
        raise

async def ensure_dataset_exists():
    """Create dataset if it doesn't exist"""
    try:
        database.client.get_dataset(settings.BIGQUERY_DATASET)
        logger.info(f"Dataset {settings.BIGQUERY_DATASET} already exists")
    except NotFound:
        logger.info(f"Creating dataset {settings.BIGQUERY_DATASET}")
        dataset = bigquery.Dataset(f"{settings.GOOGLE_CLOUD_PROJECT}.{settings.BIGQUERY_DATASET}")
        dataset.location = "US"  # Change to your preferred location
        database.client.create_dataset(dataset)

async def ensure_table_exists():
    """Create table if it doesn't exist with proper schema"""
    try:
        database.client.get_table(settings.FULL_TABLE_ID)
        logger.info(f"Table {settings.FULL_TABLE_ID} already exists")
    except NotFound:
        logger.info(f"Creating table {settings.FULL_TABLE_ID}")
        
        schema = [
            bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("address", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("score", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("is_active", "BOOLEAN", mode="REQUIRED"),
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("last_updated", "TIMESTAMP", mode="REQUIRED"),
        ]
        
        table = bigquery.Table(settings.FULL_TABLE_ID, schema=schema)
        database.client.create_table(table)

async def close_bigquery_connection():
    """Close BigQuery connection"""
    if database.client:
        database.client.close()
        logger.info("Disconnected from BigQuery")

def get_client():
    """Dependency to get the BigQuery client"""
    return database.client