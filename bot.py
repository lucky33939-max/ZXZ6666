from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from db import get_user, get_pool
from payment import create_invoice

import random
from datetime import datetime

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

dp = Dispatcher()


def menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📦 租赁888号码", callback_data="rent"),
            InlineKeyboardButton(text="🌍 国际号码", callback_data="buy")
        ],
        [
            InlineKeyboardButton(text="💰 余额充值", callback_data="topup"),
            InlineKeyboardButton(text="👤 个人中心", callback_data="profile")
        ]
    ])


@dp.message(Command("start"))
async def start(msg: types.Message):

    user = await get_user(msg.from_user.id)

    await msg.answer(
        f"💎 VIP系统\n\n💰 余额: {user['balance']} USDT",
        reply_markup=menu()
    )


@dp.callback_query()
async def cb(call: types.CallbackQuery):
    await call.answer()

    user_id = call.from_user.id
    pool = get_pool()

    if call.data == "rent":

        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM numbers LIMIT 10")

        keyboard = []

        for r in rows:

            if r["status"] == "free":
                status = "🟢 空闲"
            elif r["status"] == "locked":
                status = "🟡 已锁定"
            else:
                status = "🔴 已售"

            keyboard.append([
                InlineKeyboardButton(
                    text=f"{status} {r['number']}",
                    callback_data=f"select_{r['id']}"
                )
            ])

        await call.message.edit_text(
            "📦 号码列表",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    elif call.data.startswith("select_"):

        num_id = int(call.data.split("_")[1])

        async with pool.acquire() as conn:

            row = await conn.fetchrow(
                "SELECT * FROM numbers WHERE id=$1",
                num_id
            )

            if row["status"] == "locked" and row["locked_until"] > datetime.utcnow():
                await call.answer("⚠️ 已被占用")
                return

            await conn.execute("""
            UPDATE numbers
            SET status='locked',
                locked_by=$1,
                locked_until=NOW() + INTERVAL '5 minutes'
            WHERE id=$2
            """, user_id, num_id)

        await call.message.answer(
            f"🔒 已锁定\n\n📞 {row['number']}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="1个月 99U", callback_data=f"pay1_{num_id}"),
                    InlineKeyboardButton(text="3个月 268U", callback_data=f"pay3_{num_id}")
                ]
            ])
        )

    elif call.data.startswith("pay"):

        num_id = int(call.data.split("_")[1])
        amount = 99 if "pay1" in call.data else 268

        async with pool.acquire() as conn:

            row = await conn.fetchrow(
                "SELECT * FROM numbers WHERE id=$1",
                num_id
            )

            if row["locked_by"] != user_id:
                await call.answer("❌ 非本人订单")
                return

            order_id = await conn.fetchval(
                "INSERT INTO orders(user_id,amount) VALUES($1,$2) RETURNING id",
                user_id, amount
            )

        link = await create_invoice(order_id, amount)

        await call.message.answer(f"💳 订单 #{order_id}\n\n{link}")


@dp.message()
async def fallback(msg: types.Message):
    await msg.answer("⚡ 系统正常")
