from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import BOT_TOKEN
from db import get_user, get_pool
from payment import create_invoice

import random

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐ 星星", callback_data="stars"),
            InlineKeyboardButton(text="💰 充值", callback_data="topup")
        ],
        [
            InlineKeyboardButton(text="👤 我的", callback_data="profile")
        ]
    ])


@dp.message(Command("start"))
async def start(msg: types.Message):
    user = await get_user(msg.from_user.id)

    text = (
        "💎 VIP SYSTEM\n\n"
        f"👤 ID: {msg.from_user.id}\n"
        f"💰 余额: {user['balance']} USDT\n\n"
        f"🔥 在线: {random.randint(10,50)}"
    )

    await msg.answer(text, reply_markup=menu())


@dp.callback_query()
async def cb(call: types.CallbackQuery):
    await call.answer("⚡")

    user_id = call.from_user.id
    pool = get_pool()

    if call.data == "stars":
        await call.message.edit_text(
            "⭐ 选择套餐",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="50⭐ = 1$", callback_data="buy_1")]
            ])
        )

    elif call.data == "buy_1":

        async with pool.acquire() as conn:
            order_id = await conn.fetchval(
                "INSERT INTO orders(user_id,amount) VALUES($1,1) RETURNING id",
                user_id
            )

        link = await create_invoice(order_id, 1)

        # 💣 FIX CRASH
        if not link:
            link = "❌ Payment error"

        await call.message.answer(
            f"💳 订单 #{order_id}\n\n{link}"
        )

    elif call.data == "topup":
        await call.message.edit_text("💰 充值中...", reply_markup=menu())

    elif call.data == "profile":
        user = await get_user(user_id)

        await call.message.edit_text(
            f"👤 用户\n💰 {user['balance']} USDT",
            reply_markup=menu()
        )


@dp.message()
async def fallback(msg: types.Message):
    await msg.answer("⚡ OK")
