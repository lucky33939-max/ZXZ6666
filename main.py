from fastapi import FastAPI, Request
import asyncio

from bot import dp, bot
from db import init_db, get_pool

app = FastAPI()


# =========================
# ROOT CHECK
# =========================
@app.get("/")
async def root():
    return {"ok": True}


# =========================
# TELEGRAM WEBHOOK
# =========================
@app.post("/")
async def webhook(request: Request):
    data = await request.json()

    # 🔥 chống lag + timeout
    asyncio.create_task(dp.feed_raw_update(bot, data))

    return {"ok": True}

# =========================
# PAYMENT WEBHOOK
# =========================
@app.post("/payment-hook")
async def payment(request: Request):
    data = await request.json()

    if data.get("payment_status") == "finished":

        order_id = int(data.get("order_id", 0))
        pool = get_pool()

        async with pool.acquire() as conn:

            # =========================
            # UPDATE ORDER
            # =========================
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

            user_id = row["user_id"]

            # =========================
            # 💰 CỘNG TIỀN USER
            # =========================
            await conn.execute(
                "UPDATE users SET balance=balance+$1 WHERE id=$2",
                row["amount"], user_id
            )

            # =========================
            # 💸 REF SYSTEM
            # =========================
            ref = await conn.fetchval(
                "SELECT ref_by FROM users WHERE id=$1",
                user_id
            )

            if ref:
                commission = float(row["amount"]) * 0.1
                await conn.execute(
                    "UPDATE users SET profit=profit+$1 WHERE id=$2",
                    commission, ref
                )

            # =========================
            # 🎯 AUTO DELIVERY
            # =========================
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

                # 🔒 mark number sold
                await conn.execute("""
                UPDATE numbers
                SET status='sold'
                WHERE locked_by=$1
                """, user_id)

                await bot.send_message(
                    user_id,
                    f"""
🎉 <b>购买成功</b>

━━━━━━━━━━━━━━
👤 用户名: <code>{acc['username']}</code>
🔑 密码: <code>{acc['password']}</code>
━━━━━━━━━━━━━━

⚠️ 请立即修改密码
"""
                )
            else:
                await bot.send_message(
                    user_id,
                    "⚠️ 暂无库存，请联系客服"
                )

    return {"ok": True}


# =========================
# 🔓 AUTO UNLOCK
# =========================
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


# =========================
# STARTUP
# =========================
@app.on_event("startup")
async def startup():
    await init_db()

    # 🔥 chạy background
    asyncio.create_task(unlock_worker())

    print("✅ SYSTEM READY")
