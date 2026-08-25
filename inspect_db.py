import asyncio
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import create_async_engine
import os

DB_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/skuphase"

async def main():
    engine = create_async_engine(DB_URL, echo=False)
    async with engine.begin() as conn:
        # Get the columns for users table
        result = await conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """))
        rows = result.fetchall()
        print("=" * 60)
        print("USERS TABLE SCHEMA IN DATABASE:")
        print("=" * 60)
        for col_name, data_type in rows:
            print(f"  {col_name:25} {data_type}")
        print("=" * 60)
    await engine.dispose()

asyncio.run(main())
