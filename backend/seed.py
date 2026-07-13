"""Seed script to create a demo user. Run: python seed.py"""
import asyncio
from app.database import AsyncSessionLocal, init_db
from app.models.user import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed():
    await init_db()
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.email == "demo@chatwithdata.com"))
        if result.scalar_one_or_none():
            print("Demo user already exists.")
            return

        user = User(
            email="demo@chatwithdata.com",
            name="Demo User",
            hashed_password=pwd_context.hash("demo1234"),
        )
        db.add(user)
        await db.commit()
        print("Demo user created: demo@chatwithdata.com / demo1234")


if __name__ == "__main__":
    asyncio.run(seed())
