#!/usr/bin/env python3
"""
Script to check MongoDB connection and data
Run this to verify your database setup
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def check_database():
    print("Checking MongoDB connection and data...")
    
    # Use your connection string
    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")  # Update if needed
    DATABASE_NAME = os.getenv("DB_NAME", "crypto_tracker")
    COLLECTION_NAME = os.getenv("WALLETS_COLLECTION", "smart_wallets")

    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        
        print(f"Connected to: {MONGODB_URL}")
        print(f"Database: {DATABASE_NAME}")
        print(f"Collection: {COLLECTION_NAME}")
        
        # Check connection
        server_info = await client.server_info()
        print(f"MongoDB Version: {server_info.get('version', 'Unknown')}")
        
        # Count documents
        total_count = await collection.count_documents({})
        print(f"Total wallets in collection: {total_count}")
        
        if total_count == 0:
            print("\n❌ No wallets found in the collection!")
            print("This is why your frontend shows 'No wallets found'")
            
            # Ask to create sample data
            create_sample = input("\nWould you like to create sample wallet data? (y/n): ")
            if create_sample.lower() == 'y':
                await create_sample_data(collection)
        else:
            print("\n✅ Found wallet data!")
            
            # Show sample data
            sample_wallets = await collection.find({}).limit(3).to_list(length=3)
            print("\nSample wallets:")
            for i, wallet in enumerate(sample_wallets, 1):
                print(f"{i}. Address: {wallet.get('address', 'N/A')[:20]}...")
                print(f"   Score: {wallet.get('score', 'N/A')}")
                print(f"   Active: {wallet.get('is_active', 'N/A')}")
                print()
        
        # Test the specific query your frontend uses
        print("Testing frontend query...")
        frontend_query = {"score": {"$gte": 0, "$lte": 10}}
        frontend_count = await collection.count_documents(frontend_query)
        print(f"Wallets matching frontend filter: {frontend_count}")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Error connecting to MongoDB: {e}")
        print("\nPossible issues:")
        print("1. MongoDB connection string is incorrect")
        print("2. MongoDB server is not running")
        print("3. Network connectivity issues")
        print("4. Authentication problems")

async def create_sample_data(collection):
    """Create sample wallet data for testing"""
    from datetime import datetime
    
    sample_wallets = [
        {
            "address": "0x1234567890123456789012345678901234567890",
            "score": 8,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "last_updated": datetime.utcnow()
        },
        {
            "address": "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
            "score": 6,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "last_updated": datetime.utcnow()
        },
        {
            "address": "0x9876543210987654321098765432109876543210",
            "score": 4,
            "is_active": False,
            "created_at": datetime.utcnow(),
            "last_updated": datetime.utcnow()
        }
    ]
    
    try:
        result = await collection.insert_many(sample_wallets)
        print(f"✅ Created {len(result.inserted_ids)} sample wallets")
        print("You should now see data in your frontend!")
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")

if __name__ == "__main__":
    asyncio.run(check_database())