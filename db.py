import asyncpg
import asyncio

DB_CONFIG = {
    "user": "postgres",
    "password": "password",
    "database": "botdb",
    "host": "localhost",
    "port": 5432
}

_pool = None


# =========================
# INIT POOL
# =========================
async def init_db():
    global _pool

    if _pool is None:
        _pool = await asyncpg.create_pool(
            **DB_CONFIG,
            min_size=1,
            max_size=10
        )


def get_pool():
    if _pool is None:
        raise RuntimeError("DB not initialized. Call init_db() first.")
    return _pool


# =========================
# CREATE TABLES
# =========================
async def create_tables():
    pool = get_pool()

    async with pool.acquire() as conn:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id BIGINT PRIMARY KEY,
            balance NUMERIC(12,2) DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS orders (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(id),
            amount NUMERIC(12,2),
            type TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT,
            amount NUMERIC(12,2),
            type TEXT,
            source TEXT,
            reference_id BIGINT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)


# =========================
# USER FUNCTIONS
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

            user = await conn.fetchrow(
                "SELECT * FROM users WHERE id=$1",
                user_id
            )

        # 🔥 QUAN TRỌNG: luôn return dict
        return dict(user)

# =========================
# BALANCE UPDATE
# =========================
async def add_balance(user_id: int, amount: float, order_id: int):
    pool = get_pool()

    async with pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "UPDATE users SET balance = balance + $1 WHERE id=$2",
                amount, user_id
            )

            await conn.execute("""
                INSERT INTO transactions(user_id, amount, type, source, reference_id)
                VALUES($1,$2,'credit','order',$3)
            """, user_id, amount, order_id)


# =========================
# ORDER UPDATE (PAYMENT SUCCESS)
# =========================
async def mark_order_paid(order_id: int):
    pool = get_pool()

    async with pool.acquire() as conn:
        order = await conn.fetchrow(
            "SELECT * FROM orders WHERE id=$1",
            order_id
        )

        if not order:
            return None

        if order["status"] == "paid":
            return order

        await conn.execute(
            "UPDATE orders SET status='paid' WHERE id=$1",
            order_id
        )

        # ADD BALANCE
        await add_balance(order["user_id"], float(order["amount"]), order_id)

        return order
