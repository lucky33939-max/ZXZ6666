from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from bot import dp, bot
from db import init_db, db_pool

app = FastAPI()

# ✅ ROOT FIX
@app.get("/")
async def root():
    return {"ok": True}

# ✅ TELEGRAM WEBHOOK
@app.post("/")
async def telegram_webhook(request: Request):
    data = await request.json()
    await dp.feed_raw_update(bot, data)
    return {"ok": True}

# ✅ PAYMENT WEBHOOK
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

# ✅ ADMIN
@app.get("/admin", response_class=HTMLResponse)
async def admin():
    return open("index.html").read()

# ✅ STARTUP FIX (QUAN TRỌNG)
@app.on_event("startup")
async def startup():
    await init_db()
    print("✅ DB READY")
