from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import BOT_TOKEN
from db import get_user, get_pool
from payment import create_invoice

import random

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()


# =========================
# MENU GRID
# =========================
def menu():
    return InlineKeyboardMarkup(inline_keyboard=[

        [
            InlineKeyboardButton(text="💎 VIP会员", callback_data="vip"),
            InlineKeyboardButton(text="⭐ 星星充值", callback_data="stars")
        ],

        [
            InlineKeyboardButton(text="📦 租号码", callback_data="rent"),
            InlineKeyboardButton(text="🛒 买号码", callback_data="buy")
        ],

        [
            InlineKeyboardButton(text="💰 余额充值", callback_data="topup"),
            InlineKeyboardButton(text="👤 个人中心", callback_data="profile")
        ],

        [
            InlineKeyboardButton(text="🔥 热门专区", callback_data="hot"),
            InlineKeyboardButton(text="🎁 礼物商城", callback_data="gift")
        ]
    ])


# =========================
# START (CARD STYLE)
# =========================
@dp.message(Command("start"))
async def start(msg: types.Message):
    user = await get_user(msg.from_user.id)

    text = (
        "💎 <b>VIP BANK SYSTEM</b>\n\n"
        f"👤 用户: {msg.from_user.id}\n"
        f"💰 余额: {user['balance']} USDT\n\n"
        "━━━━━━━━━━━━━━\n"
        f"🔥 在线: {random.randint(50,150)}\n"
        f"💸 今日成交: {random.randint(500,3000)}U\n"
        "━━━━━━━━━━━━━━\n"
        "⚡ 自动系统 · 秒到账"
    )

    # ✅ ALWAYS SAFE
    await msg.answer(text, reply_markup=menu())


# =========================
# CALLBACK
# =========================
@dp.callback_query()
async def cb(call: types.CallbackQuery):
    await call.answer("⚡ 加载中...")

    user_id = call.from_user.id
    pool = get_pool()

    # ⭐ STARS
    if call.data == "stars":
        await call.message.edit_text(
            "⭐ <b>选择套餐</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="50⭐ = 1$", callback_data="buy_1"),
                    InlineKeyboardButton(text="100⭐ = 2$", callback_data="buy_2")
                ],
                [InlineKeyboardButton(text="🔙 返回", callback_data="back")]
            ])
        )

    # 💳 BUY
    elif call.data.startswith("buy_"):
        amount = int(call.data.split("_")[1])

        async with pool.acquire() as conn:
            order_id = await conn.fetchval(
                "INSERT INTO orders(user_id,amount) VALUES($1,$2) RETURNING id",
                user_id, amount
            )

        link = await create_invoice(order_id, amount)

        if not link:
            link = "❌ 支付失败，请重试"

        await call.message.answer(
            f"💳 <b>订单 #{order_id}</b>\n\n{link}"
        )

    # 💰 TOPUP
    elif call.data == "topup":
        await call.message.edit_text(
            "💰 <b>充值金额</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="10U", callback_data="buy_10"),
                    InlineKeyboardButton(text="50U", callback_data="buy_50")
                ],
                [
                    InlineKeyboardButton(text="100U", callback_data="buy_100"),
                    InlineKeyboardButton(text="500U", callback_data="buy_500")
                ],
                [InlineKeyboardButton(text="🔙 返回", callback_data="back")]
            ])
        )

    # 👤 PROFILE
    elif call.data == "profile":
        user = await get_user(user_id)

        await call.message.edit_text(
            f"👤 <b>个人中心</b>\n\n💰 余额: {user['balance']} USDT",
            reply_markup=menu()
        )

    # 🔥 HOT
    elif call.data == "hot":
        await call.message.edit_text(
            f"""
🔥 <b>热门推荐</b>

👑 靓号: +888****  
💰 价格: 3000U  

🔥 {random.randint(20,80)} 人正在查看
⚠️ 即将售完
""",
            reply_markup=menu()
        )

    # 🎁 GIFT
    elif call.data == "gift":
        await call.message.edit_text(
            """
🎁 <b>礼物商城</b>

💝 10U - 2000U  
⚡ 秒到账
""",
            reply_markup=menu()
        )

    # 🔙 BACK
    elif call.data == "back":
        user = await get_user(user_id)

        await call.message.edit_text(
            f"💎 VIP SYSTEM\n💰 {user['balance']} USDT",
            reply_markup=menu()
        )


# =========================
# FALLBACK
# =========================
@dp.message()
async def fallback(msg: types.Message):
    await msg.answer("⚡ 系统运行正常")
