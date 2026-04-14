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
        max_inactive_connection_lifetime=60
    )

    async with db_pool.acquire() as conn:

        # =========================
        # USERS
        # =========================
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id BIGINT PRIMARY KEY,
            balance NUMERIC DEFAULT 0,
            ref_by BIGINT,
            profit NUMERIC DEFAULT 0,
            vip BOOLEAN DEFAULT FALSE
        );
        """)

        # =========================
        # ORDERS
        # =========================
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            user_id BIGINT,
            amount NUMERIC,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)

        # ⚡ index tăng tốc
        await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_orders_user
        ON orders(user_id);
        """)

        # =========================
        # NUMBERS (KHO SỐ)
        # =========================
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

        # ⚡ index trạng thái
        await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_numbers_status
        ON numbers(status);
        """)

        # =========================
        # ACCOUNTS (HÀNG)
        # =========================
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id SERIAL PRIMARY KEY,
            number_id INT,
            username TEXT,
            password TEXT,
            status TEXT DEFAULT 'free'
        );
        """)

        await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_accounts_status
        ON accounts(status);
        """)

    print("✅ DATABASE READY")


# =========================
# GET POOL
# =========================
def get_pool():
    if db_pool is None:
        raise RuntimeError("❌ DB NOT INITIALIZED")
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
                "INSERT INTO users(id,balance) VALUES($1,0)",
                user_id
            )
            return {
                "balance": 0,
                "profit": 0,
                "vip": False
            }

        return dict(user)


# =========================
# (OPTION) ADD BALANCE
# =========================
async def add_balance(user_id: int, amount: float):
    pool = get_pool()

    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET balance=balance+$1 WHERE id=$2",
            amount, user_id
        )


# =========================
# (OPTION) CREATE ORDER
# =========================
async def create_order(user_id: int, amount: float):
    pool = get_pool()

    async with pool.acquire() as conn:
        return await conn.fetchval(
            "INSERT INTO orders(user_id,amount) VALUES($1,$2) RETURNING id",
            user_id, amount
        )
