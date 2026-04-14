import asyncpg
from config import DATABASE_URL

db_pool = None


# =========================
# INIT DATABASE
# =========================
async def init_db():
    global db_pool

    db_pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=10,
        command_timeout=60
    )

    async with db_pool.acquire() as conn:

        # USERS TABLE
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id BIGINT PRIMARY KEY,
            balance NUMERIC DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)

        # ORDERS TABLE
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            amount NUMERIC,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)

    return db_pool


# =========================
# GET POOL (ANTI IMPORT LOOP)
# =========================
def get_pool():
    return db_pool


# =========================
# GET USER
# =========================
async def get_user(user_id: int):
    pool = get_pool()

    async with pool.acquire() as conn:
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


# =========================
# ADD BALANCE
# =========================
async def add_balance(user_id: int, amount: float):
    pool = get_pool()

    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET balance = balance + $1 WHERE id=$2",
            amount, user_id
        )


# =========================
# CREATE ORDER
# =========================
async def create_order(user_id: int, amount: float):
    pool = get_pool()

    async with pool.acquire() as conn:
        order_id = await conn.fetchval(
            "INSERT INTO orders(user_id, amount) VALUES($1,$2) RETURNING id",
            user_id, amount
        )

        return order_id


# =========================
# COMPLETE ORDER
# =========================
async def complete_order(order_id: int):
    pool = get_pool()

    async with pool.acquire() as conn:

        await conn.execute(
            "UPDATE orders SET status='paid' WHERE id=$1",
            order_id
        )

        row = await conn.fetchrow(
            "SELECT * FROM orders WHERE id=$1",
            order_id
        )

        if row:
            await conn.execute(
                "UPDATE users SET balance = balance + $1 WHERE id=$2",
                row["amount"], row["user_id"]
            )

        return row
