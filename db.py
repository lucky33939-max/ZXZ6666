import asyncpg
from config import DATABASE_URL

db = None

async def init_db():
    global db
    db = await asyncpg.create_pool(DATABASE_URL)

    async with db.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id BIGINT PRIMARY KEY,
            balance FLOAT DEFAULT 0
        );
        """)

        await conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            amount FLOAT,
            status TEXT DEFAULT 'pending'
        );
        """)

async def get_user(user_id):
    async with db.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM users WHERE id=$1", user_id)

        if not user:
            await conn.execute(
                "INSERT INTO users(id) VALUES($1)", user_id
            )
            return {"balance": 0}

        return dict(user)
