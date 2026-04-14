import os
import asyncio
import asyncpg
import time
import random
import logging

from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# ================= INIT =================
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()
app = FastAPI()
db = None

# ================= CACHE =================
user_cache = {}
last_click = {}

# ================= DB =================
async def init_db():
    global db
    db = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=3,
        command_timeout=3
    )

    await db.execute("""
    CREATE TABLE IF NOT EXISTS users (
        telegram_id BIGINT PRIMARY KEY,
        balance FLOAT DEFAULT 0
    );
    """)

    await db.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id SERIAL PRIMARY KEY,
        user_id BIGINT,
        product TEXT,
        amount INT,
        price FLOAT,
        status TEXT,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """)

    print("✅ DB READY")

# ================= ANTI SPAM =================
def anti_spam(user_id):
    now = time.time()
    if user_id in last_click and now - last_click[user_id] < 1:
        return True
    last_click[user_id] = now
    return False

# ================= USER =================
async def get_user(user_id):
    if user_id in user_cache:
        return user_cache[user_id]

    user = await db.fetchrow(
        "SELECT * FROM users WHERE telegram_id=$1",
        user_id
    )

    if not user:
        await db.execute(
            "INSERT INTO users(telegram_id, balance) VALUES($1,0)",
            user_id
        )
        user = {"telegram_id": user_id, "balance": 0}

    user_cache[user_id] = user
    return user

# ================= MENU =================
MAIN_MENU = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💎 开通会员", callback_data="vip")],
    [InlineKeyboardButton(text="⭐ 购买星星", callback_data="stars")],
    [InlineKeyboardButton(text="🔥 靓号市场", callback_data="numbers")],
    [InlineKeyboardButton(text="💰 余额充值", callback_data="topup")],
    [InlineKeyboardButton(text="👤 个人中心", callback_data="profile")]
])

# ================= START =================
@dp.message()
async def start(msg: types.Message):
    user_id = msg.from_user.id

    if anti_spam(user_id):
        return

    await get_user(user_id)

    if msg.text == "/start":
        await msg.answer(
            "🚀 <b>欢迎使用系统</b>\n请选择功能👇",
            reply_markup=MAIN_MENU
        )

# ================= CALLBACK =================
@dp.callback_query()
async def handle(call: types.CallbackQuery):
    user_id = call.from_user.id

    if anti_spam(user_id):
        await call.answer("⚡ 操作太快")
        return

    await call.answer("⚡ 处理中...")

    try:
        # ===== PROFILE =====
        if call.data == "profile":
            user = await get_user(user_id)

            await call.message.edit_text(f"""
👤 <b>个人中心</b>

🆔 ID: {user_id}
💰 余额: {user['balance']} USDT
""", reply_markup=MAIN_MENU)

        # ===== STARS =====
        elif call.data == "stars":
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="50⭐ / 1$", callback_data="buy_50")],
                [InlineKeyboardButton(text="100⭐ / 2$", callback_data="buy_100")],
                [InlineKeyboardButton(text="500⭐ / 6$", callback_data="buy_500")]
            ])
            await call.message.edit_text("⭐ 选择套餐", reply_markup=kb)

        # ===== BUY =====
        elif call.data.startswith("buy"):
            amount = int(call.data.split("_")[1])
            price_map = {50:1,100:2,500:6}
            price = price_map.get(amount,1)

            user = await get_user(user_id)

            # 💰 balance pay
            if user["balance"] >= price:
                await db.execute("""
                UPDATE users SET balance = balance - $1
                WHERE telegram_id=$2
                """, price, user_id)

                await call.message.answer(f"✅ 支付成功 ⭐ {amount}")
                return

            # 🧾 create order
            order_id = await db.fetchval("""
            INSERT INTO orders(user_id, product, amount, price, status)
            VALUES($1,$2,$3,$4,'pending') RETURNING id
            """, user_id, "stars", amount, price)

            await call.message.answer(f"""
🧾 <b>订单 #{order_id}</b>

⭐ 数量: {amount}
💰 金额: {price} USDT

💳 地址:
<code>TXXXXXXX</code>

⏳ 等待支付
""")

        # ===== NUMBERS =====
        elif call.data == "numbers":
            online = random.randint(10,50)
            sold = random.randint(20,100)

            await call.message.edit_text(f"""
👑 <b>VIP 靓号</b>

+44 → 70U
+1 → 75U

🔥 {online} 人正在看
👥 今日已售 {sold}
""", reply_markup=MAIN_MENU)

        # ===== TOPUP =====
        elif call.data == "topup":
            await call.message.edit_text("""
💰 充值地址:

<code>TXXXXXXX</code>
""", reply_markup=MAIN_MENU)

    except Exception as e:
        print("ERROR:", e)

# ================= WEBHOOK =================
@app.post("/{token}")
async def webhook(token: str, request: Request):
    if token != BOT_TOKEN:
        return {"ok": False}

    data = await request.json()
    update = types.Update(**data)

    asyncio.create_task(dp.feed_update(bot, update))

    return {"ok": True}

# ================= ROOT =================
@app.get("/")
async def root():
    return {"status": "running"}

# ================= STARTUP =================
@app.on_event("startup")
async def startup():
    await init_db()
