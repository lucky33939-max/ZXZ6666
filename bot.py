from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from db import get_user, get_pool

import random

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

dp = Dispatcher()


# =========================
# MENU
# =========================
def menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛒 账号市场", callback_data="list"),
            InlineKeyboardButton(text="💎 VIP号码", callback_data="vip")
        ],
        [
            InlineKeyboardButton(text="⭐ 星星充值", callback_data="stars"),
            InlineKeyboardButton(text="💰 余额充值", callback_data="topup")
        ],
        [
            InlineKeyboardButton(text="📊 订单记录", callback_data="orders"),
            InlineKeyboardButton(text="🎁 邀请赚钱", callback_data="ref")
        ]
    ])


# =========================
# START
# =========================
@dp.message(Command("start"))
async def start(msg: types.Message):

    user = await get_user(msg.from_user.id)
    if not user:
        user = {"balance": 0}

    await msg.answer_photo(
        photo="https://i.imgur.com/8Km9tLL.png",
        caption=f"""
💎 <b>GLOBAL VIP SYSTEM</b>

━━━━━━━━━━━━━━
👤 用户ID: <code>{msg.from_user.id}</code>  
💰 余额: <b>{user['balance']} USDT</b>  
━━━━━━━━━━━━━━

🔥 在线用户: {random.randint(120,300)}  
💸 今日成交: {random.randint(80,200)} 单  
""",
        reply_markup=menu()
    )


# =========================
# CALLBACK
# =========================
@dp.callback_query()
async def cb(call: types.CallbackQuery):

    try:
        await call.answer()
    except:
        pass

    # 🛒 MARKET
    if call.data == "list":
        await call.message.edit_text("🛒 Account List", reply_markup=menu())

    elif call.data == "country":
        await call.message.edit_text("🌍 Market", reply_markup=menu())

    elif call.data == "stars":
        await call.message.answer("⭐ Stars")

    elif call.data == "vip":
        await call.message.edit_text("💎 VIP", reply_markup=menu())

    elif call.data == "back":
        user = await get_user(call.from_user.id)
        if not user:
            user = {"balance": 0}

        await call.message.edit_text(f"""
💎 <b>GLOBAL VIP SYSTEM</b>

💰 余额: {user['balance']} USDT
""", reply_markup=menu())


# =========================
# FALLBACK
# =========================
@dp.message()
async def fallback(msg: types.Message):
    await msg.answer("⚡ 系统正常运行")
