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


# 💸 PAYMENT + DELIVERY + REF
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

            if not row:
                return {"ok": True}

            # 💰 cộng tiền user
            await conn.execute(
                "UPDATE users SET balance=balance+$1 WHERE id=$2",
                row["amount"], row["user_id"]
            )

            # 💸 REF COMMISSION
            ref = await conn.fetchval(
                "SELECT ref_by FROM users WHERE id=$1",
                row["user_id"]
            )

            if ref:
                commission = float(row["amount"]) * 0.1
                await conn.execute(
                    "UPDATE users SET profit=profit+$1 WHERE id=$2",
                    commission, ref
                )

            # 🎯 AUTO ACCOUNT DELIVERY
            acc = await conn.fetchrow("""
            SELECT * FROM accounts
            WHERE status='free'
            LIMIT 1
            """)

            if acc:
                await conn.execute(
                    "UPDATE accounts SET status='used' WHERE id=$1",
                    acc["id"]
                )

                await bot.send_message(
                    row["user_id"],
                    f"""
🎉 购买成功

👤 用户名: {acc['username']}
🔑 密码: {acc['password']}

⚠️ 请立即修改密码
"""
                )
            else:
                await bot.send_message(
                    row["user_id"],
                    "⚠️ 暂无账号库存，请联系客服"
                )

    return {"ok": True}


# 🔓 AUTO UNLOCK
async def unlock_worker():
    while True:
        pool = get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
            UPDATE numbers
            SET status='free',
                locked_by=NULL
            WHERE status='locked'
            AND locked_until < NOW()
            """)
        await asyncio.sleep(30)


@app.on_event("startup")
async def startup():
    await init_db()
    asyncio.create_task(unlock_worker())
    print("✅ SYSTEM READY")
