import os
import asyncpg
import random
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

# ================= FOMO =================
def fomo():
    return random.randint(5, 25), random.randint(1, 5)

# ================= MENU =================
def menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👑 Số VIP", callback_data="numbers")],
        [InlineKeyboardButton(text="🔥 Thuê 888", callback_data="rent")],
        [InlineKeyboardButton(text="💎 Premium", callback_data="premium")]
    ])

# ================= REGISTER =================
def register(dp, tenant_id, bot):

    # ===== MESSAGE =====
    @dp.message()
    async def msg(msg: types.Message):
        text = (msg.text or "").lower()

        if text.startswith("/start"):
            await db.execute("""
                INSERT INTO users (tenant_id, telegram_id)
                VALUES ($1,$2)
                ON CONFLICT DO NOTHING
            """, tenant_id, msg.from_user.id)

            await msg.answer("🚀 Welcome", reply_markup=menu())

    # ===== CALLBACK =====
    @dp.callback_query()
    async def cb(call: types.CallbackQuery):

        view, stock = fomo()

        # ===== NUMBERS =====
        if call.data == "numbers":
            await call.message.edit_text(f"""
╔════════════════════╗
     👑 VIP NUMBERS
╚════════════════════╝

🇬🇧 +44 → 70U  
🇺🇸 +1 → 75U  

━━━━━━━━━━━━━━━━━━
🔥 {view} người đang xem
⚡ Còn {stock} số
""",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛒 Mua ngay", callback_data="buy")]
            ]))

        # ===== 888 =====
        elif call.data == "rent":
            await call.message.edit_text(f"""
╔════════════════════╗
       🔥 888 VIP
╚════════════════════╝

1 tháng = 99U  
3 tháng = 268U  

━━━━━━━━━━━━━━━━━━
🔥 {view} người đang xem
⚡ Còn {stock} slot
""",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔥 Thuê ngay", callback_data="buy")]
            ]))

        # ===== PREMIUM =====
        elif call.data == "premium":
            await call.message.edit_text("""
💎 PREMIUM

3 tháng = 15U  
6 tháng = 20U  
1 năm = 36U
""",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Buy", callback_data="buy")]
            ]))

        # ===== BUY =====
        elif call.data == "buy":

            # fake lock
            if random.random() < 0.3:
                await call.answer("⚠️ Có người vừa đặt!", show_alert=True)

            user = await db.fetchrow("""
                SELECT id FROM users 
                WHERE telegram_id=$1 AND tenant_id=$2
            """, call.from_user.id, tenant_id)

            if not user:
                await call.message.answer("❌ /start trước")
                return

            order = await db.fetchrow("""
                INSERT INTO orders (tenant_id, user_id, product_id, amount)
                VALUES ($1,$2,1,70)
                RETURNING id
            """, tenant_id, user["id"])

            tenant = await db.fetchrow(
                "SELECT * FROM tenants WHERE id=$1", tenant_id
            )

            # ===== INVOICE =====
            await call.message.answer(f"""
╔════════════════════╗
        🧾 HOÁ ĐƠN
╚════════════════════╝

👤 User: {call.from_user.id}
📦 VIP Number
💰 70 USDT

━━━━━━━━━━━━━━━━━━
💳 TRC20:
TXYZ-XXXX-XXXX

📌 Nội dung:
ORDER {order['id']}

━━━━━━━━━━━━━━━━━━
⏳ Chờ thanh toán

🆔 #{order['id']}
""")

            # ===== ADMIN =====
            await bot.send_message(
                tenant["admin_id"],
                f"""
📥 ĐƠN MỚI

👤 {call.from_user.id}
💰 70U
🆔 #{order['id']}
"""
            )

# ================= STARTUP =================
@app.on_event("startup")
async def startup():
    await init_db()

    rows = await db.fetch("SELECT * FROM tenants")

    print("🔥 TENANTS:", rows)

    for r in rows:
        token = (r["bot_token"] or "").strip()

        print("✅ LOAD BOT:", token)

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

    print("🔥 WEBHOOK:", token)

    data = await request.json()

    if token not in bots:
        print("❌ TOKEN NOT FOUND")
        print("AVAILABLE:", list(bots.keys()))
        return {"ok": False}

    bot = bots[token]
    dp = dispatchers[token]

    update = types.Update(**data)

    await dp.feed_update(bot, update)

    return {"ok": True}

# ================= TEST =================
@app.get("/")
async def root():
    return {"status": "ok"}
