from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from db import get_user, get_pool
from payment import create_invoice

import random
from datetime import datetime, timedelta

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
# START + REF
# =========================
@dp.message(Command("start"))
async def start(msg: types.Message):

    args = msg.text.split()

    ref = None
    if len(args) > 1:
        try:
            ref = int(args[1])
        except:
            pass

    user = await get_user(msg.from_user.id)

    if ref and ref != msg.from_user.id:
        async with get_pool().acquire() as conn:
            await conn.execute(
                "UPDATE users SET ref_by=$1 WHERE id=$2",
                ref, msg.from_user.id
            )

    text = (
        "💎 <b>VIP 系统</b>\n\n"
        f"👤 用户ID: {msg.from_user.id}\n"
        f"💰 余额: {user['balance']} USDT\n\n"
        "━━━━━━━━━━━━━━\n"
        f"🔥 在线: {random.randint(50,150)}\n"
        "━━━━━━━━━━━━━━"
    )

    await msg.answer(text, reply_markup=menu())


# =========================
# CALLBACK
# =========================
@dp.callback_query()
async def cb(call: types.CallbackQuery):
    await call.answer("⚡")

    user_id = call.from_user.id
    pool = get_pool()

    # =========================
    # 📦 888 LIST
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

        keyboard.append([InlineKeyboardButton(text="🔙 返回", callback_data="back")])

        await call.message.edit_text(
            "📦 <b>888号码列表</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    # =========================
    # 🔒 LOCK NUMBER
    # =========================
    elif call.data.startswith("select_"):

        num_id = int(call.data.split("_")[1])

        async with pool.acquire() as conn:

            count = await conn.fetchval("""
            SELECT COUNT(*) FROM numbers
            WHERE locked_by=$1 AND status='locked'
            """, user_id)

            if count >= 2:
                await call.answer("⚠️ 已锁定太多号码")
                return

            row = await conn.fetchrow(
                "SELECT * FROM numbers WHERE id=$1",
                num_id
            )

            if row["status"] == "locked":
                await call.answer("⚠️ 已被占用")
                return

            vip = await conn.fetchval(
                "SELECT vip FROM users WHERE id=$1",
                user_id
            )

            minutes = 10 if vip else 5

            await conn.execute("""
            UPDATE numbers
            SET status='locked',
                locked_by=$1,
                locked_until=NOW() + ($2 || ' minutes')::interval
            WHERE id=$3
            """, user_id, minutes, num_id)

        await call.message.answer(
            f"""
🔒 已锁定号码

📞 {row['number']}

⏳ 请在 {minutes} 分钟内支付

💰 价格:
1个月 → 99U  
3个月 → 268U
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

        if "pay1" in call.data:
            amount = 99
        else:
            amount = 268

        async with pool.acquire() as conn:

            row = await conn.fetchrow(
                "SELECT * FROM numbers WHERE id=$1",
                num_id
            )

            if row["locked_by"] != user_id:
                await call.answer("❌ 非本人订单")
                return

            order_id = await conn.fetchval("""
            INSERT INTO orders(user_id,amount)
            VALUES($1,$2)
            RETURNING id
            """, user_id, amount)

        link = await create_invoice(order_id, amount)

        if not link:
            link = "❌ 支付失败"

        await call.message.answer(
            f"💳 <b>订单 #{order_id}</b>\n\n{link}"
        )

    # =========================
    # 🌍 INTERNATIONAL
    # =========================
    elif call.data == "buy":

        await call.message.edit_text(
            "🌍 选择国家",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🇺🇸 USA", callback_data="usa")],
                [InlineKeyboardButton(text="🇨🇦 Canada", callback_data="ca")],
                [InlineKeyboardButton(text="🇬🇧 UK", callback_data="uk")],
                [InlineKeyboardButton(text="🔙 返回", callback_data="back")]
            ])
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
            f"💎 VIP 系统\n💰 {user['balance']} USDT",
            reply_markup=menu()
        )


# =========================
# FALLBACK
# =========================
@dp.message()
async def fallback(msg: types.Message):
    await msg.answer("⚡ 系统运行正常")from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from db import get_user, get_pool
from payment import create_invoice

import random
from datetime import datetime, timedelta

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
# START + REF
# =========================
@dp.message(Command("start"))
async def start(msg: types.Message):

    args = msg.text.split()

    ref = None
    if len(args) > 1:
        try:
            ref = int(args[1])
        except:
            pass

    user = await get_user(msg.from_user.id)

    if ref and ref != msg.from_user.id:
        async with get_pool().acquire() as conn:
            await conn.execute(
                "UPDATE users SET ref_by=$1 WHERE id=$2",
                ref, msg.from_user.id
            )

    text = (
        "💎 <b>VIP 系统</b>\n\n"
        f"👤 用户ID: {msg.from_user.id}\n"
        f"💰 余额: {user['balance']} USDT\n\n"
        "━━━━━━━━━━━━━━\n"
        f"🔥 在线: {random.randint(50,150)}\n"
        "━━━━━━━━━━━━━━"
    )

    await msg.answer(text, reply_markup=menu())


# =========================
# CALLBACK
# =========================
@dp.callback_query()
async def cb(call: types.CallbackQuery):
    await call.answer("⚡")

    user_id = call.from_user.id
    pool = get_pool()

    # =========================
    # 📦 888 LIST
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

        keyboard.append([InlineKeyboardButton(text="🔙 返回", callback_data="back")])

        await call.message.edit_text(
            "📦 <b>888号码列表</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    # =========================
    # 🔒 LOCK NUMBER
    # =========================
    elif call.data.startswith("select_"):

        num_id = int(call.data.split("_")[1])

        async with pool.acquire() as conn:

            count = await conn.fetchval("""
            SELECT COUNT(*) FROM numbers
            WHERE locked_by=$1 AND status='locked'
            """, user_id)

            if count >= 2:
                await call.answer("⚠️ 已锁定太多号码")
                return

            row = await conn.fetchrow(
                "SELECT * FROM numbers WHERE id=$1",
                num_id
            )

            if row["status"] == "locked":
                await call.answer("⚠️ 已被占用")
                return

            vip = await conn.fetchval(
                "SELECT vip FROM users WHERE id=$1",
                user_id
            )

            minutes = 10 if vip else 5

            await conn.execute("""
            UPDATE numbers
            SET status='locked',
                locked_by=$1,
                locked_until=NOW() + ($2 || ' minutes')::interval
            WHERE id=$3
            """, user_id, minutes, num_id)

        await call.message.answer(
            f"""
🔒 已锁定号码

📞 {row['number']}

⏳ 请在 {minutes} 分钟内支付

💰 价格:
1个月 → 99U  
3个月 → 268U
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

        if "pay1" in call.data:
            amount = 99
        else:
            amount = 268

        async with pool.acquire() as conn:

            row = await conn.fetchrow(
                "SELECT * FROM numbers WHERE id=$1",
                num_id
            )

            if row["locked_by"] != user_id:
                await call.answer("❌ 非本人订单")
                return

            order_id = await conn.fetchval("""
            INSERT INTO orders(user_id,amount)
            VALUES($1,$2)
            RETURNING id
            """, user_id, amount)

        link = await create_invoice(order_id, amount)

        if not link:
            link = "❌ 支付失败"

        await call.message.answer(
            f"💳 <b>订单 #{order_id}</b>\n\n{link}"
        )

    # =========================
    # 🌍 INTERNATIONAL
    # =========================
    elif call.data == "buy":

        await call.message.edit_text(
            "🌍 选择国家",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🇺🇸 USA", callback_data="usa")],
                [InlineKeyboardButton(text="🇨🇦 Canada", callback_data="ca")],
                [InlineKeyboardButton(text="🇬🇧 UK", callback_data="uk")],
                [InlineKeyboardButton(text="🔙 返回", callback_data="back")]
            ])
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
            f"💎 VIP 系统\n💰 {user['balance']} USDT",
            reply_markup=menu()
        )


# =========================
# FALLBACK
# =========================
@dp.message()
async def fallback(msg: types.Message):
    await msg.answer("⚡ 系统运行正常")
