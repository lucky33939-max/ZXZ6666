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
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👑 Numbers", callback_data="numbers")],
        [InlineKeyboardButton(text="🔥 Rent 888 (HOT)", callback_data="rent888")],
        [
            InlineKeyboardButton(text="💎 Premium", callback_data="premium"),
            InlineKeyboardButton(text="🎁 Gifts", callback_data="gifts")
        ]
    ])
    return kb

# ================= REGISTER =================
def register(dp, tenant_id, bot):

    # ===== START =====
    @dp.message()
    async def handle_msg(msg: types.Message):
        print("MSG:", msg.text)

        text = (msg.text or "").lower()

        if text.startswith("/start"):
            await db.execute("""
                INSERT INTO users (tenant_id, telegram_id)
                VALUES ($1,$2)
                ON CONFLICT DO NOTHING
            """, tenant_id, msg.from_user.id)

            await msg.answer("🚀 Welcome", reply_markup=main_menu())
            return

        if text == "buy":
            await msg.answer("👉 Chọn sản phẩm trong menu")
            return

    # ===== CALLBACK =====
    @dp.callback_query()
    async def handle_callback(call: types.CallbackQuery):
        print("CALL:", call.data)

        # ===== NUMBERS =====
        if call.data == "numbers":
            text = """
👑 SIM LIST

+44 → 70U  
+1 tứ quý → 75U  
Thường → 60U
"""
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛒 Buy", callback_data="buy_sim")]
            ])
            await call.message.edit_text(text, reply_markup=kb)

        # ===== 888 =====
        elif call.data == "rent888":
            text = """
🔥 888 VIP

1 tháng = 99U  
3 tháng = 268U  

+888 0469 5721  
+888 0743 9525  
"""
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔥 Thuê ngay", callback_data="buy_888")]
            ])
            await call.message.edit_text(text, reply_markup=kb)

        # ===== PREMIUM =====
        elif call.data == "premium":
            text = """
💎 PREMIUM

3 tháng = 15U  
6 tháng = 20U  
1 năm = 36U
"""
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Buy", callback_data="buy_pre")]
            ])
            await call.message.edit_text(text, reply_markup=kb)

        # ===== GIFT =====
        elif call.data == "gifts":
            await call.message.edit_text("🎁 Gifts từ 10U → 2000U")

        # ===== ORDER =====
        elif call.data.startswith("buy_"):

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

            # gửi admin
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
    print("🔥 WEBHOOK HIT")

    data = await request.json()
    print("DATA:", data)

    if token not in bots:
        print("❌ TOKEN NOT FOUND")
        return {"ok": False}

    bot = bots[token]
    dp = dispatchers[token]

    update = types.Update(**data)

    # 🔥 FIX QUAN TRỌNG
    await dp.feed_update(bot, update)

    return {"ok": True}
