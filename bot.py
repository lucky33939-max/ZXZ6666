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


# =========================
# MENU
# =========================
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


# =========================
# START
# =========================
@dp.message(Command("start"))
async def start(msg: types.Message):

    user = await get_user(msg.from_user.id)

    await msg.answer(
        f"💎 VIP系统\n\n💰 余额: {user['balance']} USDT\n\n🔥 在线: {random.randint(30,100)}",
        reply_markup=menu()
    )


# =========================
# CALLBACK
# =========================
@dp.callback_query()
async def cb(call: types.CallbackQuery):
    await call.answer()

    user_id = call.from_user.id
    pool = get_pool()

    # =========================
    # 📦 LIST
    # =========================
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

        keyboard.append([
            InlineKeyboardButton(text="🔙 返回", callback_data="back")
        ])

        await call.message.edit_text(
            "📦 号码列表",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    # =========================
    # 🔒 LOCK
    # =========================
    elif call.data.startswith("select_"):

        num_id = int(call.data.split("_")[1])

        async with pool.acquire() as conn:

            row = await conn.fetchrow(
                "SELECT * FROM numbers WHERE id=$1",
                num_id
            )

            if not row:
                await call.answer("❌ 不存在")
                return

            # 🔥 FIX crash None
            if row["status"] == "locked":
                if row["locked_until"] and row["locked_until"] > datetime.utcnow():
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
            f"""
🔒 已锁定

📞 {row['number']}

⏳ 请5分钟内支付
""",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="1个月 99U", callback_data=f"pay1_{num_id}"),
                    InlineKeyboardButton(text="3个月 268U", callback_data=f"pay3_{num_id}")
                ]
            ])
        )

    # =========================
    # 💰 PAYMENT
    # =========================
    elif call.data.startswith("pay"):

        num_id = int(call.data.split("_")[1])
        amount = 99 if "pay1" in call.data else 268

        async with pool.acquire() as conn:

            row = await conn.fetchrow(
                "SELECT * FROM numbers WHERE id=$1",
                num_id
            )

            if not row:
                await call.answer("❌ 不存在")
                return

            if row["locked_by"] != user_id:
                await call.answer("❌ 非本人订单")
                return

            order_id = await conn.fetchval(
                "INSERT INTO orders(user_id,amount) VALUES($1,$2) RETURNING id",
                user_id, amount
            )

        link = await create_invoice(order_id, amount)

        await call.message.answer(
            f"💳 订单 #{order_id}\n\n{link}"
        )

    # =========================
    # PROFILE
    # =========================
    elif call.data == "profile":

        user = await get_user(user_id)

        await call.message.edit_text(
            f"👤 用户中心\n\n💰 余额: {user['balance']} USDT",
            reply_markup=menu()
        )

    # =========================
    # BACK
    # =========================
    elif call.data == "back":

        user = await get_user(user_id)

        await call.message.edit_text(
            f"💎 VIP系统\n\n💰 {user['balance']} USDT",
            reply_markup=menu()
        )


# =========================
# FALLBACK
# =========================
@dp.message()
async def fallback(msg: types.Message):
    await msg.answer("⚡ 系统正常运行")
