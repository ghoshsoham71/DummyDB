import asyncio
from src.db.session import AsyncSessionLocal
from src.db.models import GenerationJob
from sqlalchemy import select

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(GenerationJob))
        jobs = result.scalars().all()
        print(f"Total jobs: {len(jobs)}")
        for j in jobs:
            print(f"ID: {j.id}, Status: {j.status}, Progress: {j.progress}, Error: {j.error_message}")

if __name__ == "__main__":
    asyncio.run(check())
