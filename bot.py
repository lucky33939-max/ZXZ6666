from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN, ADMIN_ID
from db import get_user, get_pool

import os
import uvicorn
import random

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)

dp = Dispatcher()


# =========================
# MENU APP STYLE
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
# START (BANNER)
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
""",
        reply_markup=menu()
    )


# =========================
# CALLBACK MAIN
# =========================
@dp.callback_query()
async def cb(call: types.CallbackQuery):

    try:
        await call.answer()
    except:
        pass

    user_id = call.from_user.id
    pool = get_pool()

    # =========================
    # 🛒 ACCOUNT MARKET
    # =========================
    if call.data == "list":

        await call.message.edit_text(f"""
🛒 <b>Account List</b>

━━━━━━━━━━━━━━

+1 530-955-0999 — 75U  
+1 559-468-0999 — 75U  
+1 971-403-2222 — 75U  
+1 802-945-9666 — 75U  

━━━━━━━━━━━━━━

+44 7988 587333 — 70U  
+44 7429 918444 — 70U  

━━━━━━━━━━━━━━
🔥 {random.randint(30,120)} users viewing
""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌍 Select Market", callback_data="country")],
            [InlineKeyboardButton(text="🔙 Back", callback_data="back")]
        ])
    )

    # =========================
    # 🌍 MARKET
    # =========================
    elif call.data == "country":

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
            [InlineKeyboardButton(text="🇮🇳 India - $0.51", callback_data="c_india")],
            [InlineKeyboardButton(text="🇵🇭 Philippines - $0.79", callback_data="c_ph")],
            [InlineKeyboardButton(text="🇹🇭 Thailand - $1.20", callback_data="c_th")],
            [InlineKeyboardButton(text="🇦🇪 UAE - $2.85", callback_data="c_uae")],
            [InlineKeyboardButton(text="🇬🇧 UK VIP - $60", callback_data="c_uk")],
            [InlineKeyboardButton(text="💎 888号码 - $99", callback_data="rent")],
            [InlineKeyboardButton(text="🔙 Back", callback_data="back")]
        ])
    )

    # =========================
    # ⭐ STARS
    # =========================
    elif call.data == "stars":

        await call.message.answer_photo(
            photo="https://i.imgur.com/ZF6s192.png",
            caption="""
⭐ <b>Telegram Stars</b>

━━━━━━━━━━━━━━
⭐ 50 = 1U  
⭐ 100 = 2U  
⭐ 200 = 4U  
⭐ 500 = 10U  
⭐ 1000 = 20U  
━━━━━━━━━━━━━━

👇 请选择充值方式
""",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💎 给当前账号充值", callback_data="top_self")],
                [InlineKeyboardButton(text="🎁 给他人充值", callback_data="top_other")],
                [InlineKeyboardButton(text="💱 兑换TON", callback_data="ton")],
                [InlineKeyboardButton(text="❌ 关闭", callback_data="back")]
            ])
        )

    # =========================
    # 💎 VIP
    # =========================
    elif call.data == "vip":

        await call.message.edit_text(f"""
💎 <b>Telegram Premium</b>

━━━━━━━━━━━━━━
👤 用户: {call.from_user.username}
━━━━━━━━━━━━━━

请选择套餐 👇
""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="3个月 / 15U", callback_data="vip3")],
            [InlineKeyboardButton(text="半年 / 25U", callback_data="vip6")],
            [InlineKeyboardButton(text="一年 / 35U", callback_data="vip12")],
            [
                InlineKeyboardButton(text="❌ 取消", callback_data="back"),
                InlineKeyboardButton(text="👨‍💼 联系客服", url="https://t.me/your_support")
            ]
        ])
    )

    # =========================
    # 🔙 BACK
    # =========================
    elif call.data == "back":
        user = await get_user(user_id)

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
