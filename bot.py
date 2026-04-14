from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN
from db import db, get_user
from payment import create_invoice

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher()

def menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐ 星星充值", callback_data="stars"),
            InlineKeyboardButton(text="💰 余额充值", callback_data="topup")
        ],
        [
            InlineKeyboardButton(text="👤 个人中心", callback_data="profile"),
            InlineKeyboardButton(text="💬 客服", url="https://t.me/your_support")
        ]
    ])

@dp.message()
async def start(msg: types.Message):
    user = await get_user(msg.from_user.id)

    await msg.answer(f"""
💎 VIP SYSTEM

ID: {msg.from_user.id}
余额: {user['balance']} USDT
""", reply_markup=menu())


@dp.callback_query()
async def cb(call: types.CallbackQuery):
    await call.answer("⚡")

    user_id = call.from_user.id

    if call.data == "stars":
        await call.message.edit_text("""
⭐ 选择充值:

50⭐ = 1$
100⭐ = 2$
""", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="50⭐", callback_data="buy_1")]
        ]))

    elif call.data == "buy_1":
        async with db.acquire() as conn:
            order_id = await conn.fetchval("""
            INSERT INTO orders(user_id, amount)
            VALUES($1,1)
            RETURNING id
            """, user_id)

        link = await create_invoice(order_id, 1)

        await call.message.answer(f"""
💳 支付订单 #{order_id}

👉 {link}
""")

    elif call.data == "profile":
        user = await get_user(user_id)

        await call.message.edit_text(f"""
👤 个人中心

余额: {user['balance']} USDT
""", reply_markup=menu())
