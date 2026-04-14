import asyncio
import asyncpg
import os
import time
import logging

from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties

# =====================
# CONFIG
# =====================

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

# =====================
# INIT
# =====================

app = FastAPI()
dp = Dispatcher()

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

db = None

# =====================
# CACHE
# =====================

user_cache = {}
last_click = {}

# =====================
# DB CONNECT
# =====================

async def init_db():
    global db
    db = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=1,
        max_size=3,
        command_timeout=3
    )
    print("✅ DB READY")

# =====================
# USER
# =====================

async def get_user(user_id):
    if user_id in user_cache:
        return user_cache[user_id]

    user = await db.fetchrow(
        "SELECT * FROM users WHERE telegram_id=$1",
        user_id
    )

    if not user:
        await db.execute(
            "INSERT INTO users(telegram_id, balance) VALUES($1, 0)",
            user_id
        )
        user = {"telegram_id": user_id, "balance": 0}

    user_cache[user_id] = user
    return user

# =====================
# ANTI SPAM
# =====================

def anti_spam(user_id):
    now = time.time()
    if user_id in last_click and now - last_click[user_id] < 1:
        return True
    last_click[user_id] = now
    return False

# =====================
# MENU
# =====================

MAIN_MENU = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="💎 开通会员", callback_data="vip")],
    [InlineKeyboardButton(text="⭐ 购买星星", callback_data="stars")],
    [InlineKeyboardButton(text="👤 个人中心", callback_data="profile")],
    [InlineKeyboardButton(text="💰 余额充值", callback_data="topup")],
])

# =====================
# HANDLER
# =====================

@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id

    if anti_spam(user_id):
        return

    await get_user(user_id)

    if message.text == "/start":
        await message.answer(
            "👋 欢迎使用系统\n请选择功能👇",
            reply_markup=MAIN_MENU
        )
    else:
        await message.answer("⚡ 系统处理中...")

# =====================
# CALLBACK
# =====================

@dp.callback_query()
async def handle_callback(call: types.CallbackQuery):
    user_id = call.from_user.id

    if anti_spam(user_id):
        await call.answer("⚡ 请慢一点")
        return

    await call.answer("⚡ 处理中...")

    try:
        if call.data == "profile":
            user = await get_user(user_id)

            text = f"""
👤 用户中心

ID: {user_id}
余额: {user.get("balance", 0)} USDT
"""
            await call.message.edit_text(text, reply_markup=MAIN_MENU)

        elif call.data == "topup":
            await call.message.edit_text(
                "💰 选择充值金额",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="10 USDT", callback_data="pay_10")],
                    [InlineKeyboardButton(text="50 USDT", callback_data="pay_50")],
                    [InlineKeyboardButton(text="100 USDT", callback_data="pay_100")]
                ])
            )

        else:
            await call.message.answer("🚀 功能开发中...")

    except:
        pass  # tránh lỗi edit message

# =====================
# WEBHOOK
# =====================

@app.post("/{token}")
async def webhook(token: str, request: Request):
    if token != BOT_TOKEN:
        return {"ok": False}

    data = await request.json()
    update = types.Update(**data)

    asyncio.create_task(process_update(update))

    return {"ok": True}

async def process_update(update):
    try:
        await dp.feed_update(bot, update)
    except Exception as e:
        print("ERROR:", e)

# =====================
# STARTUP
# =====================

@app.on_event("startup")
async def startup():
    await init_db()
