"""
Drop just the users table so it gets recreated with the correct schema.
"""
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/skuphase"

async def drop_users_table():
    """Drop the users table."""
    engine = create_async_engine(DB_URL, echo=False)
    
    try:
        async with engine.begin() as conn:
            print("Dropping users table...")
            await conn.execute(text("DROP TABLE IF EXISTS users CASCADE"))
            print("SUCCESS: users table dropped")
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        await engine.dispose()

if __name__ == '__main__':
    asyncio.run(drop_users_table())
