from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from pathlib import Path
import asyncio

from bot import dp, bot
from db import init_db

app = FastAPI()

db_pool = None

# ROOT
@app.get("/")
async def root():
    return {"ok": True}

# TELEGRAM WEBHOOK
@app.post("/")
async def telegram_webhook(request: Request):
    data = await request.json()

    # ⚡ chạy async tránh lag
    asyncio.create_task(dp.feed_raw_update(bot, data))

    return {"ok": True}

# PAYMENT WEBHOOK
@app.post("/payment-hook")
async def payment_hook(request: Request):
    data = await request.json()

    if data.get("payment_status") == "finished":
        order_id = int(data["order_id"])

        async with db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE orders SET status='paid' WHERE id=$1",
                order_id
            )

            row = await conn.fetchrow(
                "SELECT * FROM orders WHERE id=$1", order_id
            )

        if row:
            await bot.send_message(
                row["user_id"],
                f"💎 支付成功 #{order_id}"
            )

    return {"ok": True}

# ADMIN PAGE
@app.get("/admin", response_class=HTMLResponse)
async def admin():
    return Path("index.html").read_text()

# STARTUP
@app.on_event("startup")
async def startup():
    global db_pool
    db_pool = await init_db()
    print("✅ DB READY")
