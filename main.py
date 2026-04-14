from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

from bot import dp, bot
from db import init_db, db

app = FastAPI()

# ===== TELEGRAM WEBHOOK =====
@app.post("/")
async def telegram_webhook(request: Request):
    data = await request.json()
    await dp.feed_raw_update(bot, data)
    return {"ok": True}

# ===== PAYMENT WEBHOOK =====
@app.post("/payment-hook")
async def payment_hook(request: Request):
    data = await request.json()

    if data.get("payment_status") == "finished":
        order_id = int(data["order_id"])

        async with db.acquire() as conn:
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
                f"💎 支付成功\n订单 #{order_id}"
            )

    return {"ok": True}

# ===== ADMIN API =====
@app.get("/admin/stats")
async def stats():
    async with db.acquire() as conn:
        users = await conn.fetchval("SELECT COUNT(*) FROM users")
        orders = await conn.fetchval("SELECT COUNT(*) FROM orders")
        money = await conn.fetchval(
            "SELECT COALESCE(SUM(amount),0) FROM orders WHERE status='paid'"
        )

    return {"users": users, "orders": orders, "revenue": money}

@app.get("/admin/orders")
async def orders():
    async with db.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM orders ORDER BY id DESC")

    return [dict(r) for r in rows]

# ===== ADMIN PAGE =====
@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    with open("index.html", encoding="utf-8") as f:
        return f.read()

# ===== START =====
@app.on_event("startup")
async def startup():
    await init_db()
