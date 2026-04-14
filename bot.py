from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import BOT_TOKEN
from db import get_user
from db import get_pool
from payment import create_invoice

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


def menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐ 购买星星", callback_data="stars"),
            InlineKeyboardButton(text="💰 充值余额", callback_data="topup")
        ],
        [
            InlineKeyboardButton(text="👤 个人中心", callback_data="profile"),
            InlineKeyboardButton(text="💬 客服", url="https://t.me/ZXZ368")
        ]
    ])


@dp.message(Command("start"))
async def start(msg: types.Message):
    user = await get_user(msg.from_user.id)

    if not user:
        user = {"balance": 0}

    text = (
        "💎 VIP SYSTEM\n\n"
        f"👤 ID: {msg.from_user.id}\n"
        f"💰 余额: {user['balance']} USDT"
    )

    await msg.answer(text, reply_markup=menu())


@dp.callback_query()
async def cb(call: types.CallbackQuery):
    await call.answer()

    user_id = call.from_user.id

    if call.data == "stars":
        await call.message.edit_text(
            "⭐ 选择套餐:\n\n50⭐ = 1$",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="50⭐", callback_data="buy_1")]
            ])
        )

    elif call.data == "buy_1":
        async with db_pool.acquire() as conn:
            order_id = await conn.fetchval(
                "INSERT INTO orders(user_id, amount) VALUES($1,1) RETURNING id",
                user_id
            )

        link = await create_invoice(order_id, 1)

        await call.message.answer(
            f"💳 订单 #{order_id}\n\n👉 {link}"
        )

    elif call.data == "profile":
        user = await get_user(user_id)

        if not user:
            user = {"balance": 0}

        await call.message.edit_text(
            f"👤 个人中心\n\n💰 余额: {user['balance']} USDT",
            reply_markup=menu()
        )


# fallback
@dp.message()
async def fallback(msg: types.Message):
    await msg.answer("⚡ 系统正常运行")
