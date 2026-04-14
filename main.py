import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse

from bot import dp, bot
from db import init_db, get_pool, create_tables

logging.basicConfig(level=logging.INFO)

app = FastAPI()


# =========================
# ROOT
# =========================
@app.get("/")
async def root():
    return {"status": "ok"}


# =========================
# TELEGRAM WEBHOOK
# =========================
@app.post("/")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()

        # chạy async không block
        asyncio.create_task(dp.feed_raw_update(bot, data))

        return {"ok": True}

    except Exception:
        logging.exception("Telegram webhook error")
        raise HTTPException(500, "Webhook failed")


# =========================
# PAYMENT WEBHOOK (SAFE)
# =========================
@app.post("/payment-hook")
async def payment_hook(request: Request):
    try:
        data = await request.json()

        logging.info(f"Payment hook: {data}")

        # ✅ validate status
        if data.get("payment_status") != "finished":
            return {"ok": True}

        order_id = data.get("order_id")
        if not order_id:
            raise HTTPException(400, "Missing order_id")

        order_id = int(order_id)

        # ✅ FIX: không dùng await
        pool = get_pool()

        async with pool.acquire() as conn:
            async with conn.transaction():

                # 🔥 LOCK chống double payment
                row = await conn.fetchrow(
                    "SELECT * FROM orders WHERE id=$1 FOR UPDATE",
                    order_id
                )

                if not row:
                    raise HTTPException(404, "Order not found")

                if row["status"] == "paid":
                    logging.warning(f"Duplicate payment: {order_id}")
                    return {"ok": True}

                # update order
                await conn.execute(
                    "UPDATE orders SET status='paid' WHERE id=$1",
                    order_id
                )

                # update balance
                await conn.execute(
                    "UPDATE users SET balance = balance + $1 WHERE id=$2",
                    row["amount"], row["user_id"]
                )

                # log transaction (VERY IMPORTANT)
                await conn.execute("""
                    INSERT INTO transactions(user_id, amount, type, source, reference_id)
                    VALUES($1,$2,'credit','order',$3)
                """, row["user_id"], row["amount"], order_id)

        # ✅ gửi message sau transaction
        try:
            await bot.send_message(
                row["user_id"],
                f"💎 Thanh toán thành công\n\n"
                f"🧾 Đơn #{order_id}\n"
                f"💰 +{row['amount']} USDT"
            )
        except Exception:
            logging.exception("Send message failed")

        return {"ok": True}

    except HTTPException:
        raise
    except Exception:
        logging.exception("Payment hook error")
        raise HTTPException(500, "Internal error")


# =========================
# ADMIN PAGE
# =========================
@app.get("/admin", response_class=HTMLResponse)
async def admin():
    file = Path("index.html")

    if file.exists():
        return file.read_text()

    return "<h1>Admin Panel Not Found</h1>"


# =========================
# HEALTH CHECK
# =========================
@app.get("/ping")
async def ping():
    return {"alive": True}


# =========================
# STARTUP
# =========================
@app.on_event("startup")
async def startup():
    await init_db()
    await create_tables()
    logging.info("✅ DB ready")
