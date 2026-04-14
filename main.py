from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from pathlib import Path
import asyncio

from bot import dp, bot
from db import init_db, get_pool

app = FastAPI()


# =========================
# ROOT CHECK
# =========================
@app.get("/")
async def root():
    return {"status": "ok"}


# =========================
# TELEGRAM WEBHOOK (ANTI LAG)
# =========================
@app.post("/")
async def telegram_webhook(request: Request):
    data = await request.json()

    # ⚡ xử lý async không block
    asyncio.create_task(dp.feed_raw_update(bot, data))

    return {"ok": True}


# =========================
# PAYMENT WEBHOOK (AUTO MONEY)
# =========================
@app.post("/payment-hook")
async def payment_hook(request: Request):
    data = await request.json()

    if data.get("payment_status") == "finished":
        order_id = int(data["order_id"])

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

            # 💰 cộng tiền vào user
            if row:
                await conn.execute(
                    "UPDATE users SET balance = balance + $1 WHERE id=$2",
                    row["amount"], row["user_id"]
                )

        if row:
            await bot.send_message(
                row["user_id"],
                f"💎 支付成功\n\n订单 #{order_id}\n💰 已到账 {row['amount']} USDT"
            )

    return {"ok": True}


# =========================
# ADMIN PAGE (WEB UI)
# =========================
@app.get("/admin", response_class=HTMLResponse)
async def admin():
    file = Path("index.html")

    if file.exists():
        return file.read_text()

    return "<h1>Admin Panel Not Found</h1>"


# =========================
# HEALTH CHECK (ANTI SLEEP)
# =========================
@app.get("/ping")
async def ping():
    return {"alive": True}


# =========================
# STARTUP (DB INIT)
# =========================
@app.on_event("startup")
async def startup():
    await init_db()
    print("✅ DB READY")
