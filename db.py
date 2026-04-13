import asyncpg
import os

db = None

async def init_db():
    global db
    db = await asyncpg.create_pool(os.getenv("DATABASE_URL"))
