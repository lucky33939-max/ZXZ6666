from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN, ADMIN_ID
from db import get_user, get_pool

import random
from datetime import datetime

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

dp = Dispatcher()


# =========================
# 💎 MENU APP STYLE
# =========================
def menu():
    return InlineKeyboardMarkup(inline_keyboard=[

        [InlineKeyboardButton(text="🛒 账号市场", callback_data="list")],

        [
            InlineKeyboardButton(text="💎 VIP号码", callback_data="vip"),
            InlineKeyboardButton(text="📦 888号码", callback_data="rent")
        ],

        [
            InlineKeyboardButton(text="🌍 全球号码", callback_data="country"),
            InlineKeyboardButton(text="⭐ 星星充值", callback_data="stars")
        ],

        [
            InlineKeyboardButton(text="💰 余额充值", callback_data="topup"),
            InlineKeyboardButton(text="📊 订单记录", callback_data="orders")
        ],

        [
            InlineKeyboardButton(text="👤 个人中心", callback_data="profile"),
            InlineKeyboardButton(text="🎁 邀请赚钱", callback_data="ref")
        ]
    ])


# =========================
# 🖼️ START + BANNER
# =========================
@dp.message(Command("start"))
async def start(msg: types.Message):

    user = await get_user(msg.from_user.id)

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

⚡ 系统稳定运行
""",
        reply_markup=menu()
    )


# =========================
# CALLBACK
# =========================
@dp.callback_query()
async def cb(call: types.CallbackQuery):
    await call.answer("⚡ 加载中...")

    user_id = call.from_user.id
    pool = get_pool()

    # =========================
    # 🌍 MARKET
    # =========================
    if call.data == "country":

        await call.message.edit_text(f"""
🌍 <b>全球号码市场</b>

━━━━━━━━━━━━━━

🇺🇸 USA VIP号码  
🇬🇧 英国号码  
🇨🇦 加拿大号码  
🇦🇪 阿联酋号码  

💎 888靓号专区  

━━━━━━━━━━━━━━
🔥 {random.randint(30,120)} 人正在浏览
""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🇺🇸 USA", callback_data="usa")],
            [InlineKeyboardButton(text="🇬🇧 UK", callback_data="uk")],
            [InlineKeyboardButton(text="🇨🇦 CA", callback_data="ca")],
            [InlineKeyboardButton(text="💎 888专区", callback_data="rent")],
            [InlineKeyboardButton(text="🔙 返回", callback_data="back")]
        ])
    )

    # =========================
    # 📦 888 LIST
    # =========================
    elif call.data == "rent":

        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM numbers LIMIT 10")

        text = "📦 <b>精品号码列表</b>\n━━━━━━━━━━━━━━\n\n"
        keyboard = []

        for r in rows:

            icon = "🟢" if r["status"] == "free" else "🟡"

            text += f"{icon} <code>{r['number']}</code>\n"

            keyboard.append([
                InlineKeyboardButton(
                    text=f"{r['number']}",
                    callback_data=f"select_{r['id']}"
                )
            ])

        text += f"\n━━━━━━━━━━━━━━\n🔥 {random.randint(20,80)} 人正在查看"

        keyboard.append([InlineKeyboardButton(text="🔙 返回", callback_data="back")])

        await call.message.edit_text(
            text,
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

        await call.message.answer(f"""
🔒 <b>号码锁定成功</b>

📞 <code>{row['number']}</code>

━━━━━━━━━━━━━━
⏳ 请在5分钟内支付  
🔥 {random.randint(20,80)} 人正在抢购  
━━━━━━━━━━━━━━

💰 价格:
1个月 → <b>{row['price_1m']} USDT</b>  
3个月 → <b>{row['price_3m']} USDT</b>
""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💳 1个月", callback_data=f"pay1_{num_id}"),
                InlineKeyboardButton(text="💳 3个月", callback_data=f"pay3_{num_id}")
            ]
        ])
        )

    # =========================
    # 💳 ORDER
    # =========================
    elif call.data.startswith("pay"):

        num_id = int(call.data.split("_")[1])
        amount = 99 if "pay1" in call.data else 268

        async with pool.acquire() as conn:

            order_id = await conn.fetchval(
                "INSERT INTO orders(user_id,amount) VALUES($1,$2) RETURNING id",
                user_id, amount
            )

        await call.message.answer(f"""
💎 <b>VIP订单</b>

━━━━━━━━━━━━━━
🆔 <code>#{order_id}</code>  
💰 <b>{amount} USDT</b>  
━━━━━━━━━━━━━━

⏳ 请完成付款
""")

        await bot.send_message(
            ADMIN_ID,
            f"""
🆕 新订单

🆔 {order_id}
👤 {user_id}
💰 {amount} USDT
""",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ 已收款", callback_data=f"confirm_{order_id}"),
                    InlineKeyboardButton(text="❌ 未收款", callback_data=f"reject_{order_id}")
                ]
            ])
        )

    # =========================
    # 👤 PROFILE
    # =========================
    elif call.data == "profile":

        user = await get_user(user_id)

        await call.message.edit_text(f"""
👤 <b>个人中心</b>

━━━━━━━━━━━━━━
💰 余额: <b>{user['balance']} USDT</b>  
💸 收益: <b>{user.get('profit',0)} USDT</b>  
━━━━━━━━━━━━━━
""", reply_markup=menu())

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
    await msg.answer("⚡ 系统运行正常")
