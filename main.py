from fastapi import FastAPI, Request
import asyncio

from bot import dp, bot
from db import init_db, get_pool

app = FastAPI()


@app.get("/")
async def root():
    return {"ok": True}


@app.post("/")
async def webhook(request: Request):
    data = await request.json()

    asyncio.create_task(dp.feed_raw_update(bot, data))

    return {"ok": True}


@app.post("/payment-hook")
async def payment(request: Request):
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

            if row:
                await conn.execute(
                    "UPDATE users SET balance=balance+$1 WHERE id=$2",
                    row["amount"], row["user_id"]
                )

                await bot.send_message(
                    row["user_id"],
                    f"💎 支付成功\n+{row['amount']} USDT"
                )

    return {"ok": True}


@app.on_event("startup")
async def startup():
    await init_db()
    print("✅ READY")
