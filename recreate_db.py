"""
Drop and recreate all tables with the correct schema.
This will DELETE all existing data.
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# DB URL from environment
DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/skuphase"

async def recreate_tables():
    """Drop all tables and recreate them from models."""
    engine = create_async_engine(DB_URL, echo=True)
    
    # Import the base from models to get all model definitions
    from app.models.base import Base
    
    print("\n" + "="*70)
    print("DROPPING ALL TABLES...")
    print("="*70)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    print("\n" + "="*70)
    print("CREATING ALL TABLES...")
    print("="*70)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("\n" + "="*70)
    print("VERIFYING USERS TABLE SCHEMA...")
    print("="*70)
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """))
        rows = result.fetchall()
        for col_name, data_type in rows:
            print(f"  {col_name:25} {data_type}")
    
    await engine.dispose()
    print("\n" + "="*70)
    print("SUCCESS: Tables recreated!")
    print("="*70)

if __name__ == '__main__':
    asyncio.run(recreate_tables())
