import os
import random
import asyncpg
import logging

from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, Update
)
from aiogram.fsm.storage.memory import MemoryStorage

# ===== CONFIG =====
DATABASE_URL = os.getenv("DATABASE_URL")

logging.basicConfig(level=logging.INFO)

app = FastAPI()

bots = {}
dispatchers = {}
db = None
user_state = {}

# ================= DB =================
async def init_db():
    global db
    db = await asyncpg.create_pool(DATABASE_URL)

# ================= MENU =================
def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💎 Premium"), KeyboardButton(text="⭐ Stars")],
            [KeyboardButton(text="👑 Numbers"), KeyboardButton(text="🔥 Rent 888")],
            [KeyboardButton(text="💰 Topup"), KeyboardButton(text="👤 Profile")],
            [KeyboardButton(text="👨‍💻 Support")]
        ],
        resize_keyboard=True
    )

def stars_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="50⭐ / 1$", callback_data="star_50"),
            InlineKeyboardButton(text="100⭐ / 2$", callback_data="star_100")
        ],
        [
            InlineKeyboardButton(text="200⭐", callback_data="star_200"),
            InlineKeyboardButton(text="300⭐", callback_data="star_300")
        ],
        [
            InlineKeyboardButton(text="500⭐", callback_data="star_500"),
            InlineKeyboardButton(text="1000⭐", callback_data="star_1000")
        ]
    ])

# ================= FOMO =================
def fomo():
    return random.randint(10, 80), random.randint(5, 30)

# ================= REGISTER =================
def register(dp, tenant_id, bot):

    # ===== MESSAGE =====
    @dp.message()
    async def handle_all(msg: types.Message):
        print("📩 RECEIVED:", msg.text)

        text = (msg.text or "").lower()

        # START
        if text.startswith("/start"):
            await msg.answer("🚀 Bot Ready", reply_markup=main_menu())
            return

        # STARS
        if msg.text == "⭐ Stars":
            await msg.answer("✨ Chọn gói Stars:", reply_markup=stars_menu())
            return

        # PREMIUM
        if msg.text == "💎 Premium":
            await msg.answer("""
💎 PREMIUM

3 tháng = 15U  
6 tháng = 20U  
1 năm = 36U
""")
            return

        # NUMBERS
        if msg.text == "👑 Numbers":
            buyers, view = fomo()
            await msg.answer(f"""
👑 VIP NUMBERS

+44 → 70U  
+1 → 75U  

🔥 {view} đang xem
👥 {buyers} đã mua hôm nay
""")
            return

        # 888
        if msg.text == "🔥 Rent 888":
            await msg.answer("""
🔥 888 VIP

1 tháng = 99U  
3 tháng = 268U
""")
            return

        # PROFILE
        if msg.text == "👤 Profile":
            await msg.answer(f"""
👤 Profile

ID: {msg.from_user.id}
Balance: 0.00
""")
            return

        # TOPUP
        if msg.text == "💰 Topup":
            await msg.answer("""
💰 Nạp tiền

10U | 50U | 100U  
200U | 500U | 1000U
""")
            return

        # SUPPORT
        if msg.text == "👨‍💻 Support":
            await msg.answer("📩 Contact admin: @yourusername")
            return

        # ===== INPUT USERNAME =====
        if msg.from_user.id in user_state:
            package = user_state[msg.from_user.id]
            username = msg.text

            buyers, _ = fomo()

            await msg.answer(f"""
╔════════════════════╗
        🧾 INVOICE
╚════════════════════╝

👤 User: {username}
📦 Gói: {package}

👥 {buyers} người đã mua hôm nay

━━━━━━━━━━━━━━━━━━
💳 TRC20:
TXYZ-XXXX

⏳ Status: PENDING
""")

            del user_state[msg.from_user.id]

    # ===== CALLBACK =====
    @dp.callback_query()
    async def cb(call: types.CallbackQuery):

        # STARS SELECT
        if call.data.startswith("star_"):
            user_state[call.from_user.id] = call.data

            await call.message.answer("📩 Nhập username Telegram (@username):")

            await call.answer()

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
        dp = Dispatcher(storage=MemoryStorage())

        register(dp, r["id"], bot)

        bots[token] = bot
        dispatchers[token] = dp

    print("🚀 TOTAL BOTS:", len(bots))

# ================= WEBHOOK =================
@app.post("/{token}")
async def webhook(token: str, request: Request):
    token = token.strip()

    data = await request.json()

    print("🔥 WEBHOOK HIT")

    if token not in bots:
        print("❌ TOKEN NOT FOUND")
        return {"ok": False}

    bot = bots[token]
    dp = dispatchers[token]

    update = Update(**data)

    await dp.feed_update(bot=bot, update=update)

    return {"ok": True}

# ================= ROOT =================
@app.get("/")
async def root():
    return {"status": "ok"}
