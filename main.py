from fastapi import FastAPI, Request
import asyncio

from aiogram.types import Update

from bot import dp, bot
from db import init_db, get_pool

app = FastAPI()


@app.get("/")
async def root():
    return {"ok": True}


@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        print("🔥 UPDATE:", data)

        # 👉 delay nhỏ để DB ready
        await asyncio.sleep(1)

        update = Update.model_validate(data)
        await dp.feed_update(bot=bot, update=update)

        return {"ok": True}

    except Exception as e:
        print("❌ ERROR:", e)
        return {"ok": True}   # ⚠️ luôn trả ok để tránh 502

async def unlock_worker():
    while True:
        try:
            pool = get_pool()
            async with pool.acquire() as conn:
                await conn.execute("""
                UPDATE numbers
                SET status='free',
                    locked_by=NULL
                WHERE status='locked'
                AND locked_until < NOW()
                """)
        except Exception as e:
            print("Worker error:", e)

        await asyncio.sleep(30)


@app.on_event("startup")
async def startup():
    await init_db()
    asyncio.create_task(unlock_worker())
    print("✅ SYSTEM READY")
