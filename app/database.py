from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

class Database:
    client: AsyncIOMotorClient = None
    database = None
    collection = None

# Global database instance
database = Database()

async def connect_to_mongo():
    """Create database connection"""
    database.client = AsyncIOMotorClient(settings.MONGODB_URL)
    database.database = database.client[settings.DATABASE_NAME]
    database.collection = database.database[settings.COLLECTION_NAME]
    
    # Create indexes for better performance
    await database.collection.create_index("address", unique=True)
    await database.collection.create_index("score")
    await database.collection.create_index("is_active")
    await database.collection.create_index("created_at")
    
    print(f"Connected to MongoDB: {settings.DATABASE_NAME}.{settings.COLLECTION_NAME}")

async def close_mongo_connection():
    """Close database connection"""
    if database.client:
        database.client.close()
        print("Disconnected from MongoDB")

def get_collection():
    """Dependency to get the MongoDB collection"""
    return database.collection