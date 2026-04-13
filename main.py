import os
import asyncpg
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types

DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI()

bots = {}
dispatchers = {}
db = None

# ================= DB =================
async def init_db():
    global db
    db = await asyncpg.create_pool(DATABASE_URL)

# ================= HANDLER =================
def register(dp, tenant_id, bot):

    @dp.message()
    async def handler(msg: types.Message):
        print("MESSAGE:", msg.text)  # DEBUG

        text = (msg.text or "").strip().lower()

        # ===== START =====
        if text.startswith("/start"):
            await db.execute("""
                INSERT INTO users (tenant_id, telegram_id)
                VALUES ($1,$2)
                ON CONFLICT DO NOTHING
            """, tenant_id, msg.from_user.id)

            await msg.answer("🚀 Welcome")
            return

        # ===== BUY =====
        if text == "buy":
            user = await db.fetchrow("""
                SELECT id FROM users 
                WHERE telegram_id=$1 AND tenant_id=$2
            """, msg.from_user.id, tenant_id)

            if not user:
                await msg.answer("❌ Please send /start first")
                return

            order = await db.fetchrow("""
                INSERT INTO orders (tenant_id, user_id, product_id)
                VALUES ($1,$2,1)
                RETURNING id
            """, tenant_id, user["id"])

            tenant = await db.fetchrow(
                "SELECT * FROM tenants WHERE id=$1", tenant_id
            )

            await bot.send_message(
                tenant["admin_id"],
                f"📥 Order #{order['id']} từ {msg.from_user.id}"
            )

            await msg.answer(f"⏳ Order #{order['id']} created")
            return

        # ===== DEFAULT =====
        await msg.answer("👉 Gõ /start hoặc 'buy'")

# ================= STARTUP =================
@app.on_event("startup")
async def startup():
    await init_db()

    rows = await db.fetch("SELECT * FROM tenants")

    for r in rows:
        print("LOAD BOT:", r["bot_token"])

        bot = Bot(token=r["bot_token"])
        dp = Dispatcher()

        register(dp, r["id"], bot)

        bots[r["bot_token"]] = bot
        dispatchers[r["bot_token"]] = dp

# ================= WEBHOOK =================
@app.post("/{token}")
async def webhook(token: str, request: Request):
    if token not in bots:
        print("❌ TOKEN NOT FOUND:", token)
        return {"ok": False}

    data = await request.json()
    print("UPDATE:", data)  # DEBUG

    update = types.Update(**data)

    await dispatchers[token].process_update(update)

    return {"ok": True}
