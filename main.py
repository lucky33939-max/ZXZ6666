import os
import asyncpg
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI()

bots = {}
dispatchers = {}
db = None

# ================= DB =================
async def init_db():
    global db
    db = await asyncpg.create_pool(DATABASE_URL)

# ================= MENU =================
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👑 Numbers", callback_data="numbers")],
        [InlineKeyboardButton(text="🔥 Rent 888", callback_data="rent")],
        [InlineKeyboardButton(text="💎 Premium", callback_data="premium")]
    ])

# ================= REGISTER =================
def register(dp, tenant_id, bot):

    @dp.message()
    async def msg_handler(msg: types.Message):
        print("📩 MSG:", msg.text)

        text = (msg.text or "").strip().lower()

        if text.startswith("/start"):
            await db.execute("""
                INSERT INTO users (tenant_id, telegram_id)
                VALUES ($1,$2)
                ON CONFLICT DO NOTHING
            """, tenant_id, msg.from_user.id)

            await msg.answer("🚀 Welcome", reply_markup=main_menu())
            return

        await msg.answer("👉 Gõ /start")

    @dp.callback_query()
    async def cb_handler(call: types.CallbackQuery):
        print("🔘 CLICK:", call.data)

        if call.data == "numbers":
            await call.message.edit_text(
                "👑 SIM LIST\n+44 = 70U\n+1 = 75U",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🛒 Buy", callback_data="buy")]
                ])
            )

        elif call.data == "rent":
            await call.message.edit_text(
                "🔥 888 thuê\n1 tháng = 99U\n3 tháng = 268U",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔥 Thuê ngay", callback_data="buy")]
                ])
            )

        elif call.data == "premium":
            await call.message.edit_text(
                "💎 Premium\n3 tháng = 15U\n6 tháng = 20U\n1 năm = 36U",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Buy", callback_data="buy")]
                ])
            )

        elif call.data == "buy":
            user = await db.fetchrow("""
                SELECT id FROM users 
                WHERE telegram_id=$1 AND tenant_id=$2
            """, call.from_user.id, tenant_id)

            if not user:
                await call.message.answer("❌ /start trước")
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
                f"📥 Order #{order['id']} từ {call.from_user.id}"
            )

            await call.message.answer(f"⏳ Order #{order['id']} created")

# ================= STARTUP =================
@app.on_event("startup")
async def startup():
    await init_db()

    rows = await db.fetch("SELECT * FROM tenants")

    print("🔥 TENANTS:", rows)

    for r in rows:
        token = (r["bot_token"] or "").strip()

        print("✅ LOAD BOT:", token)

        if not token:
            continue

        bot = Bot(token=token)
        dp = Dispatcher()

        register(dp, r["id"], bot)

        bots[token] = bot
        dispatchers[token] = dp

    print("🚀 TOTAL BOTS:", len(bots))

# ================= WEBHOOK =================
@app.post("/{token}")
async def webhook(token: str, request: Request):
    token = token.strip()

    print("🔥 WEBHOOK HIT:", token)

    data = await request.json()
    print("📦 DATA:", data)

    if token not in bots:
        print("❌ TOKEN NOT FOUND:", token)
        print("📌 AVAILABLE:", list(bots.keys()))
        return {"ok": False}

    bot = bots[token]
    dp = dispatchers[token]

    update = types.Update(**data)

    await dp.feed_update(bot, update)

    return {"ok": True}
