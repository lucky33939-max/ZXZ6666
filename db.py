import asyncpg
from config import DATABASE_URL

db_pool = None


async def init_db():
    global db_pool

    db_pool = await asyncpg.create_pool(DATABASE_URL)

    async with db_pool.acquire() as conn:

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id BIGINT PRIMARY KEY,
            balance NUMERIC DEFAULT 0
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            amount NUMERIC,
            status TEXT DEFAULT 'pending'
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS numbers (
            id SERIAL PRIMARY KEY,
            number TEXT UNIQUE,
            status TEXT DEFAULT 'free',
            price_1m INT DEFAULT 99,
            price_3m INT DEFAULT 268,
            locked_by BIGINT,
            locked_until TIMESTAMP
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id SERIAL PRIMARY KEY,
            username TEXT,
            password TEXT,
            status TEXT DEFAULT 'free'
        );
        """)


def get_pool():
    return db_pool


async def get_user(user_id: int):
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE id=$1",
            user_id
        )

        if not user:
            await conn.execute(
                "INSERT INTO users(id,balance) VALUES($1,0)",
                user_id
            )
            return {"balance": 0}

        return dict(user)
