import asyncpg
from config import DATABASE_URL

db_pool = None


# =========================
# INIT DB
# =========================
async def init_db():
    global db_pool

    db_pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=5
    )

    async with db_pool.acquire() as conn:

        # USERS
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id BIGINT PRIMARY KEY,
            balance NUMERIC DEFAULT 0
        );
        """)

        # ORDERS
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            amount NUMERIC,
            status TEXT DEFAULT 'pending'
        );
        """)

    return db_pool


# =========================
# GET USER
# =========================
async def get_user(user_id: int):
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE id=$1",
            user_id
        )

        if not user:
            await conn.execute(
                "INSERT INTO users(id, balance) VALUES($1, 0)",
                user_id
            )
            return {"balance": 0}

        return dict(user)
